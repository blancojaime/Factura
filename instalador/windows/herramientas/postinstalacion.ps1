# Configura SICOM-MUNI tras copiar los archivos: base de datos, servicios, firewall, respaldos y primer arranque.
# Es idempotente: sirve tanto para instalar como para actualizar sin perder datos.
param(
    [Parameter(Mandatory = $true)][string]$Respuestas,
    [string]$InstallDirParam = ''
)
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
if ($InstallDirParam) { $script:InstallDir = $InstallDirParam.TrimEnd('\') }
$LogFile = 'instalacion.log'
function Log([string]$m) { Escribir-Log $m $LogFile }

try {
    Log '=== Instalación de SICOM-MUNI ==='
    $r = Get-Content -Raw -Path $Respuestas -Encoding UTF8 | ConvertFrom-Json
    $puerto = [int]$r.puerto
    if ($puerto -lt 1024 -or $puerto -gt 65535) { throw "Puerto inválido: $puerto" }

    # 1. Requisito: Visual C++ 2015-2022 (lo usan PostgreSQL y Python)
    $vc = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction SilentlyContinue
    if (-not $vc -or $vc.Installed -ne 1) {
        Log 'Instalando Microsoft Visual C++ Redistributable...'
        $p = Start-Process -FilePath (Join-Path $InstallDir 'prerequisitos\vc_redist.x64.exe') -ArgumentList '/install', '/quiet', '/norestart' -Wait -PassThru
        if (@(0, 1638, 3010, 1641) -notcontains $p.ExitCode) { throw "No se pudo instalar Visual C++ (código $($p.ExitCode))" }
    }

    # 2. Carpetas de datos (fuera de Program Files) con permisos restringidos
    foreach ($d in 'pgdata', 'archivos', 'respaldos', 'logs', 'config', 'cache') { New-Item -ItemType Directory -Force -Path (Join-Path $DataDir $d) | Out-Null }
    function Restringir([string]$ruta, [string]$nivelSvc = 'F') {
        # SID conocidos: SYSTEM (S-1-5-18), Administradores (S-1-5-32-544), NetworkService (S-1-5-20)
        Invocar-Nativo 'icacls.exe' @($ruta, '/inheritance:r', '/grant:r', '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F', "*S-1-5-20:(OI)(CI)$nivelSvc", '/C', '/Q') | Out-Null
        # Archivos y carpetas ya existentes: se les quita la herencia y se les da acceso explícito
        Invocar-Nativo 'icacls.exe' @((Join-Path $ruta '*'), '/inheritance:r', '/grant:r', '*S-1-5-18:F', '*S-1-5-32-544:F', "*S-1-5-20:$nivelSvc", '/T', '/C', '/Q') | Out-Null
    }

    # 3. Secretos (se crean una sola vez y se conservan en las actualizaciones)
    $archivoSecretos = Join-Path $ConfigDir 'secretos.json'
    function Clave-Aleatoria([int]$n) {
        $caracteres = (48..57) + (65..90) + (97..122)
        return -join ($caracteres | Get-Random -Count $n | ForEach-Object { [char]$_ })
    }
    if (Test-Path $archivoSecretos) {
        $sec = Get-Content -Raw $archivoSecretos | ConvertFrom-Json
    } else {
        $sec = [pscustomobject]@{ pg_super = (Clave-Aleatoria 28); pg_app = (Clave-Aleatoria 28); secret_key = (Clave-Aleatoria 64) }
        Escribir-Archivo $archivoSecretos ($sec | ConvertTo-Json)
    }

    # 4. PostgreSQL: crea el cluster la primera vez
    $bin = Join-Path $InstallDir 'pgsql\bin'
    $pgdata = Join-Path $DataDir 'pgdata'
    if (-not (Test-Path (Join-Path $pgdata 'PG_VERSION'))) {
        Log 'Creando la base de datos (initdb)...'
        $pw = Join-Path $env:TEMP ('pgpw_' + [guid]::NewGuid().ToString('N'))
        Set-Content -Path $pw -Value $sec.pg_super -Encoding ASCII -NoNewline
        try {
            $x = Invocar-Nativo (Join-Path $bin 'initdb.exe') @('-D', $pgdata, '-U', 'postgres', '-E', 'UTF8', '--locale=C', '--auth-local=scram-sha-256', '--auth-host=scram-sha-256', "--pwfile=$pw")
            Log ("initdb: " + $x.Salida)
            if ($x.Codigo -ne 0) { throw "initdb falló (código $($x.Codigo))" }
        } finally { Remove-Item $pw -Force -ErrorAction SilentlyContinue }
        $conf = @"

# --- SICOM-MUNI ---
listen_addresses = '127.0.0.1'
port = $($script:PgPuerto)
max_connections = 100
shared_buffers = 128MB
password_encryption = scram-sha-256
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%a.log'
log_truncate_on_rotation = on
log_rotation_age = 1d
log_min_duration_statement = 2000
"@
        Add-Content -Path (Join-Path $pgdata 'postgresql.conf') -Value $conf -Encoding ASCII
    }
    Restringir $pgdata

    # 5. Servicio de la base de datos
    if (-not (Get-Service -Name $SvcBd -ErrorAction SilentlyContinue)) {
        Log 'Registrando el servicio de base de datos...'
        $x = Invocar-Nativo (Join-Path $bin 'pg_ctl.exe') @('register', '-N', $SvcBd, '-D', $pgdata, '-S', 'auto', '-U', 'NT AUTHORITY\NetworkService')
        Log ("pg_ctl: " + $x.Salida)
        if ($x.Codigo -ne 0) { throw "No se pudo registrar el servicio de PostgreSQL (código $($x.Codigo))" }
        Invocar-Nativo 'sc.exe' @('description', $SvcBd, 'Base de datos PostgreSQL de SICOM-MUNI') | Out-Null
    }
    if ((Get-Service -Name $SvcBd).Status -ne 'Running') {
        try { Start-Service -Name $SvcBd -ErrorAction Stop }
        catch {
            Log ("No inició el servicio de la base de datos: " + $_.Exception.Message)
            foreach ($f in Get-ChildItem (Join-Path $pgdata 'log') -ErrorAction SilentlyContinue) { Log ("--- pgdata\log\" + $f.Name + " ---"); Log ((Get-Content $f.FullName -Tail 40 -ErrorAction SilentlyContinue) -join "`n") }
            try { Log ((Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Service Control Manager' } -MaxEvents 6 | ForEach-Object { $_.Message }) -join "`n") } catch { }
            Log ((Invocar-Nativo 'icacls.exe' @($pgdata)).Salida)
            Log ((Invocar-Nativo 'sc.exe' @('qc', $SvcBd)).Salida)
            Log ((Invocar-Nativo 'icacls.exe' @((Join-Path $pgdata 'postgresql.conf'))).Salida)
            try { Log ((Get-WinEvent -FilterHashtable @{ LogName = 'Application' } -MaxEvents 15 | Where-Object { $_.ProviderName -match 'Postgre|pg_ctl|Application Error' } | ForEach-Object { $_.ProviderName + ': ' + $_.Message }) -join "`n") } catch { }
            Log ('postgres -C: ' + (Invocar-Nativo (Join-Path $bin 'postgres.exe') @('-D', $pgdata, '-C', 'data_directory')).Salida)
            Log ('pg_ctl start (administrador): ' + (Invocar-Nativo (Join-Path $bin 'pg_ctl.exe') @('start', '-D', $pgdata, '-w', '-t', '20', '-l', (Join-Path $env:TEMP 'pgprueba.log'))).Salida)
            if (Test-Path (Join-Path $env:TEMP 'pgprueba.log')) { Log (Get-Content (Join-Path $env:TEMP 'pgprueba.log') -Raw) }
            throw
        }
    }
    $listo = $false
    for ($i = 0; $i -lt 60; $i++) {
        $x = Invocar-Nativo (Join-Path $bin 'pg_isready.exe') @('-h', '127.0.0.1', '-p', "$($script:PgPuerto)")
        if ($x.Codigo -eq 0) { $listo = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $listo) { throw 'La base de datos no inició. Revise C:\ProgramData\SICOM-MUNI\pgdata\log' }

    # 6. Rol y base de datos de la aplicación
    $env:PGPASSWORD = $sec.pg_super
    $psql = Join-Path $bin 'psql.exe'
    $base = @('-h', '127.0.0.1', '-p', "$($script:PgPuerto)", '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-q')
    $existeRol = (Invocar-Nativo $psql ($base + @('-tAc', "SELECT 1 FROM pg_roles WHERE rolname='sicom'"))).Salida
    $sql = Join-Path $env:TEMP ('sicom_' + [guid]::NewGuid().ToString('N') + '.sql')
    try {
        if ($existeRol -ne '1') { $orden = "CREATE ROLE sicom LOGIN PASSWORD '{0}';" } else { $orden = "ALTER ROLE sicom PASSWORD '{0}';" }
        Escribir-Archivo $sql ($orden -f $sec.pg_app)
        $x = Invocar-Nativo $psql ($base + @('-f', $sql))
        if ($x.Codigo -ne 0) { throw "No se pudo configurar el usuario de la base de datos: $($x.Salida)" }
    } finally { Remove-Item $sql -Force -ErrorAction SilentlyContinue }
    $existeBd = (Invocar-Nativo $psql ($base + @('-tAc', "SELECT 1 FROM pg_database WHERE datname='sicom'"))).Salida
    if ($existeBd -ne '1') {
        $x = Invocar-Nativo $psql ($base + @('-c', "CREATE DATABASE sicom OWNER sicom ENCODING 'UTF8' TEMPLATE template0"))
        if ($x.Codigo -ne 0) { throw "No se pudo crear la base de datos sicom: $($x.Salida)" }
    }
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue

    # 7. Configuración de la aplicación (.env) y fuentes para los PDF
    $ip = Ip-Local
    $url = "http://{0}:{1}" -f $ip, $puerto
    $envTexto = @"
ENV=prod
DATABASE_URL=postgresql+psycopg://sicom:$($sec.pg_app)@127.0.0.1:$($script:PgPuerto)/sicom
SECRET_KEY=$($sec.secret_key)
STATIC_DIR=$InstallDir\web
LOCAL_STORAGE_PATH=$DataDir\archivos
STORAGE_BACKEND=local
SERVIDOR_HOST=0.0.0.0
SERVIDOR_PUERTO=$puerto
PUBLIC_BASE_URL=$url
COOKIE_SECURE=false
LICENCIA_OBLIGATORIA=1
LICENCIA_DIAS_PRUEBA=30
"@
    Escribir-Archivo (Join-Path $ConfigDir '.env') $envTexto
    $fuentes = (Get-Content -Raw (Join-Path $InstallDir 'herramientas\plantillas\fonts.conf.tpl')) -replace '@INSTALL@', $InstallDir -replace '@DATA@', $DataDir
    Escribir-Archivo (Join-Path $ConfigDir 'fonts.conf') $fuentes
    Restringir $ConfigDir 'R'
    Restringir (Join-Path $DataDir 'archivos')
    Restringir (Join-Path $DataDir 'logs')
    Restringir (Join-Path $DataDir 'cache')
    Restringir (Join-Path $DataDir 'respaldos') 'R'

    # 8. Inicializa la base (migraciones, entidad, administrador, datos de demostración opcionales)
    Log 'Inicializando la base de datos del sistema...'
    $env:SICOM_ENTIDAD = [string]$r.entidad
    $env:SICOM_CIUDAD = [string]$r.ciudad
    $env:SICOM_ADMIN_USUARIO = [string]$r.adminUsuario
    $env:SICOM_ADMIN_CLAVE = [string]$r.adminClave
    $argsCli = @('inicializar')
    if ($r.demo -eq $true -or $r.demo -eq 'true' -or $r.demo -eq 1) { $argsCli += '--demo' }
    $res = Ejecutar-Cli $argsCli
    Remove-Item Env:\SICOM_ADMIN_CLAVE -ErrorAction SilentlyContinue
    Log ("cli inicializar: " + $res.Salida.Trim())
    if ($res.Codigo -ne 0) { throw "La inicialización del sistema falló (código $($res.Codigo))" }

    # 9. Licencia (opcional)
    if ($r.licencia -and (Test-Path $r.licencia)) {
        $l = Ejecutar-Cli @('activar-licencia', [string]$r.licencia)
        Log ("licencia: " + $l.Salida.Trim())
    }

    # 10. Servicio de la aplicación (WinSW)
    $dirServicio = Join-Path $ConfigDir 'servicio'
    New-Item -ItemType Directory -Force -Path $dirServicio | Out-Null
    $exe = Join-Path $dirServicio 'SICOM-MUNI-Servicio.exe'
    $xml = Join-Path $dirServicio 'SICOM-MUNI-Servicio.xml'
    $svc = Get-Service -Name $SvcApp -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne 'Stopped') { Stop-Service -Name $SvcApp -Force; $svc.WaitForStatus('Stopped', '00:00:30') }
    Copy-Item -Force -ErrorAction Stop (Join-Path $InstallDir 'herramientas\winsw.exe') $exe
    $plantilla = Get-Content -Raw (Join-Path $InstallDir 'herramientas\plantillas\servicio.xml.tpl')
    $plantilla = $plantilla.Replace('@INSTALL@', $InstallDir).Replace('@DATA@', $DataDir).Replace('@CONFIG@', $ConfigDir)
    Escribir-Archivo $xml $plantilla
    if (-not $svc) {
        Log 'Registrando el servicio de la aplicación...'
        $x = Invocar-Nativo $exe @('install')
        Log ("winsw: " + $x.Salida)
        if ($x.Codigo -ne 0) { throw "No se pudo registrar el servicio (código $($x.Codigo))" }
        Invocar-Nativo 'sc.exe' @('config', $SvcApp, 'obj=', 'NT AUTHORITY\NetworkService') | Out-Null
        Invocar-Nativo 'sc.exe' @('failure', $SvcApp, 'reset=', '86400', 'actions=', 'restart/5000/restart/10000/restart/30000') | Out-Null
    }
    Restringir $dirServicio 'R'
    try { Start-Service -Name $SvcApp -ErrorAction Stop }
    catch {
        Log ("No inició el servicio de la aplicación: " + $_.Exception.Message)
        foreach ($f in Get-ChildItem (Join-Path $DataDir 'logs') -Filter 'SICOM-MUNI-Servicio*' -ErrorAction SilentlyContinue) { Log ("--- " + $f.Name + " ---"); Log ((Get-Content $f.FullName -Tail 40 -ErrorAction SilentlyContinue) -join "`n") }
        try { Log ((Get-WinEvent -FilterHashtable @{ LogName = 'Application' } -MaxEvents 20 | Where-Object { $_.Message -match 'SICOM|python|WinSW' } | ForEach-Object { $_.ProviderName + ': ' + $_.Message }) -join "`n") } catch { }
        try { Log ((Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Service Control Manager' } -MaxEvents 6 | ForEach-Object { $_.Message }) -join "`n") } catch { }
        Log ((Invocar-Nativo 'sc.exe' @('qc', $SvcApp)).Salida)
        Log ((Invocar-Nativo 'icacls.exe' @($dirServicio)).Salida)
        Log (Get-Content $xml -Raw)
        throw
    }

    # 11. Firewall: solo la red local
    Get-NetFirewallRule -DisplayName 'SICOM-MUNI*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName "SICOM-MUNI (puerto $puerto)" -Direction Inbound -Protocol TCP -LocalPort $puerto -Action Allow -Profile Any -RemoteAddress LocalSubnet | Out-Null

    # 12. Respaldo diario automático (02:00)
    $accion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}" -Silencioso' -f (Join-Path $InstallDir 'herramientas\respaldar.ps1'))
    $disparador = New-ScheduledTaskTrigger -Daily -At '02:00'
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName 'SICOM-MUNI Respaldo diario' -Action $accion -Trigger $disparador -Principal $principal -Force | Out-Null

    # 13. Verificación final
    Log 'Esperando a que el sistema responda...'
    if (-not (Esperar-Url "http://127.0.0.1:$puerto/api/v1/salud" 120)) { throw "El sistema no respondió. Revise $LogDir\servicio.err.log" }
    $idEquipo = (Ejecutar-Cli @('id-equipo')).Salida.Trim()
    $lic = Invoke-RestMethod -Uri "http://127.0.0.1:$puerto/api/v1/licencia" -UseBasicParsing
    $nombrePc = $env:COMPUTERNAME
    function Sin-Acentos([string]$t) { return -join ($t.Normalize([Text.NormalizationForm]::FormD).ToCharArray() | Where-Object { [Globalization.CharUnicodeInfo]::GetUnicodeCategory($_) -ne 'NonSpacingMark' }) }
    $resultado = @(
        "Direccion para los usuarios de la red:  $url/",
        "Tambien:  http://${nombrePc}:$puerto/",
        "En este equipo:  http://localhost:$puerto/",
        "ID del equipo (para solicitar la licencia):  $idEquipo",
        ("Estado de la licencia:  " + (Sin-Acentos $lic.mensaje))
    )
    Escribir-Archivo (Join-Path $ConfigDir 'resultado.txt') (($resultado -join "`r`n") + "`r`n")
    Set-Content -Path (Join-Path $ConfigDir 'puerto.txt') -Value $puerto -Encoding ASCII
    $resultado | ForEach-Object { Log $_ }
    Log '=== Instalación terminada correctamente ==='
    exit 0
}
catch {
    Log ("ERROR: " + $_.Exception.Message)
    Log ($_.ScriptStackTrace)
    exit 1
}
finally {
    Remove-Item -Path $Respuestas -Force -ErrorAction SilentlyContinue
}
