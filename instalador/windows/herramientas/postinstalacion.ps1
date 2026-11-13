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

function Sin-Acentos([string]$t) { return -join ($t.Normalize([Text.NormalizationForm]::FormD).ToCharArray() | Where-Object { [Globalization.CharUnicodeInfo]::GetUnicodeCategory($_) -ne 'NonSpacingMark' }) }

# Devuelve el nombre del programa que ya usa el puerto (o $null si está libre).
function Puerto-En-Uso([int]$p) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $c) { return $null }
    $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
    if ($proc -and $proc.Path -and $proc.Path -like "$InstallDir\*") { return $null }   # es nuestro propio servicio (actualización)
    if ($proc) { return $proc.ProcessName }
    return 'otro programa'
}

# La base de datos de un intento anterior puede tener otra contraseña de "postgres" que la que se generó ahora.
# Sin perder datos: se abre el acceso local un momento, se fija la contraseña nueva y se restablece la seguridad.
function Restablecer-Clave-Postgres([string]$pgdata, [string]$bin, [string]$claveNueva) {
    Log 'La contraseña interna de la base de datos no coincide (restos de una instalación anterior): se restablece sin perder datos.'
    $hba = Join-Path $pgdata 'pg_hba.conf'
    $copia = Join-Path $pgdata 'pg_hba.conf.sicom'
    Copy-Item -LiteralPath $hba -Destination $copia -Force
    try {
        $abierto = "local all all trust`n" + "host all all 127.0.0.1/32 trust`n" + "host all all ::1/128 trust`n"
        [System.IO.File]::WriteAllText($hba, $abierto, [System.Text.Encoding]::ASCII)
        Stop-Service -Name $SvcBd -Force -ErrorAction SilentlyContinue
        try { (Get-Service $SvcBd).WaitForStatus('Stopped', '00:01:00') } catch { }
        Start-Service -Name $SvcBd -ErrorAction SilentlyContinue
        $listo = $false
        for ($i = 0; $i -lt 60; $i++) {
            if ((Invocar-Nativo (Join-Path $bin 'pg_isready.exe') @('-h', '127.0.0.1', '-p', "$($script:PgPuerto)")).Codigo -eq 0) { $listo = $true; break }
            Start-Sleep -Seconds 2
        }
        if (-not $listo) { throw 'La base de datos no arrancó al restablecer la contraseña.' }
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        $sqlC = Join-Path $DataDir ('cache\clave_' + [guid]::NewGuid().ToString('N') + '.sql')
        try {
            Escribir-Archivo $sqlC ("ALTER ROLE postgres PASSWORD '{0}';" -f $claveNueva)
            $x = Invocar-Nativo (Join-Path $bin 'psql.exe') @('-h', '127.0.0.1', '-p', "$($script:PgPuerto)", '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-q', '-f', $sqlC)
            if ($x.Codigo -ne 0) { throw "No se pudo restablecer la contraseña de la base de datos: $($x.Salida)" }
        } finally { Remove-Item $sqlC -Force -ErrorAction SilentlyContinue }
    } finally {
        # se restablece SIEMPRE la seguridad original (autenticación con contraseña)
        Copy-Item -LiteralPath $copia -Destination $hba -Force
        Remove-Item -LiteralPath $copia -Force -ErrorAction SilentlyContinue
        Stop-Service -Name $SvcBd -Force -ErrorAction SilentlyContinue
        try { (Get-Service $SvcBd).WaitForStatus('Stopped', '00:01:00') } catch { }
        Start-Service -Name $SvcBd -ErrorAction SilentlyContinue
        for ($i = 0; $i -lt 60; $i++) {
            if ((Invocar-Nativo (Join-Path $bin 'pg_isready.exe') @('-h', '127.0.0.1', '-p', "$($script:PgPuerto)")).Codigo -eq 0) { break }
            Start-Sleep -Seconds 2
        }
    }
}

# Vuelca al registro lo necesario para diagnosticar un servicio que no arranca.
function Diagnostico-Servicio([string]$nombre) {
    try { Log ((Invocar-Nativo 'sc.exe' @('qc', $nombre)).Salida) } catch { }
    try { Log ((Invocar-Nativo 'sc.exe' @('query', $nombre)).Salida) } catch { }
    foreach ($f in Get-ChildItem $LogDir -Filter 'SICOM-MUNI-Servicio*' -ErrorAction SilentlyContinue) { Log ("--- $($f.Name) ---"); Log ((Get-Content $f.FullName -Tail 40 -ErrorAction SilentlyContinue) -join "`n") }
    foreach ($f in Get-ChildItem (Join-Path $DataDir 'pgdata\log') -ErrorAction SilentlyContinue) { Log ("--- pgdata\log\$($f.Name) ---"); Log ((Get-Content $f.FullName -Tail 40 -ErrorAction SilentlyContinue) -join "`n") }
    try { Log ((Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Service Control Manager' } -MaxEvents 8 | ForEach-Object { $_.Message }) -join "`n") } catch { }
    try { Log ((Get-WinEvent -FilterHashtable @{ LogName = 'Application' } -MaxEvents 25 | Where-Object { $_.Message -match 'SICOM|python|WinSW|Postgre' } | ForEach-Object { $_.ProviderName + ': ' + $_.Message }) -join "`n") } catch { }
}

try {
    Log '=== Instalación de SICOM-MUNI ==='
    Remove-Item (Join-Path $LogDir 'ultimo-error.txt') -Force -ErrorAction SilentlyContinue
    $r = Get-Content -Raw -Path $Respuestas -Encoding UTF8 | ConvertFrom-Json
    $puerto = [int]$r.puerto
    if ($puerto -lt 1024 -or $puerto -gt 65535) { throw "Puerto inválido: $puerto" }
    Log ("Equipo: $env:COMPUTERNAME · " + [Environment]::OSVersion.VersionString + " · idioma " + (Get-Culture).Name)
    $uso = Puerto-En-Uso $puerto
    if ($uso) { throw "El puerto $puerto ya lo usa el programa '$uso'. Vuelva a ejecutar el instalador y elija otro puerto en la pantalla «Red local» (por ejemplo 8181)." }
    $uso = Puerto-En-Uso $script:PgPuerto
    if ($uso) { throw "El puerto interno $($script:PgPuerto) ya lo usa el programa '$uso'. Cierre ese programa y vuelva a ejecutar el instalador." }

    # 1. Requisito: Visual C++ 2015-2022 (lo usan PostgreSQL y Python)
    $vc = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction SilentlyContinue
    if (-not $vc -or $vc.Installed -ne 1) {
        Log 'Instalando Microsoft Visual C++ Redistributable...'
        for ($intento = 1; $intento -le 4; $intento++) {
            $p = Start-Process -FilePath (Join-Path $InstallDir 'prerequisitos\vc_redist.x64.exe') -ArgumentList '/install', '/quiet', '/norestart' -Wait -PassThru
            if ($p.ExitCode -ne 1618) { break }
            Log 'Windows está instalando otra cosa (código 1618); se reintenta en 45 segundos...'
            Start-Sleep -Seconds 45
        }
        if (@(0, 1638, 3010, 1641) -notcontains $p.ExitCode) { throw "No se pudo instalar Visual C++ (código $($p.ExitCode)). Instálelo manualmente desde la carpeta prerequisitos y vuelva a ejecutar el instalador." }
    }

    # 2. Carpetas de datos (fuera de Program Files) con permisos restringidos
    foreach ($d in 'pgdata', 'archivos', 'respaldos', 'logs', 'config', 'cache') { New-Item -ItemType Directory -Force -Path (Join-Path $DataDir $d) | Out-Null }
    function Restringir([string]$ruta, [string]$nivelSvc = 'F') {
        # SID conocidos: SYSTEM (S-1-5-18), Administradores (S-1-5-32-544), NetworkService (S-1-5-20)
        # 1) Carpeta raíz: solo esas tres cuentas, con permiso HEREDABLE (lo recibe todo lo que se cree dentro después)
        Invocar-Nativo 'icacls.exe' @($ruta, '/inheritance:r', '/grant:r', '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F', "*S-1-5-20:(OI)(CI)$nivelSvc", '/Q') | Out-Null
        # 2) Lo que ya existe dentro vuelve a HEREDAR de la raíz (/reset), de modo que las subcarpetas también
        #    transmiten el permiso a los archivos nuevos (PostgreSQL crea archivos en pg_logical, pg_wal, base...).
        #    Esto también repara instalaciones anteriores que dejaron permisos explícitos no heredables.
        if (Get-ChildItem -LiteralPath $ruta -Force -ErrorAction SilentlyContinue | Select-Object -First 1) {
            Invocar-Nativo 'icacls.exe' @((Join-Path $ruta '*'), '/reset', '/T', '/C', '/Q') | Out-Null
        }
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
        # restos de un intento anterior que no llegó a terminar: initdb exige una carpeta vacía
        if (Get-ChildItem $pgdata -Force -ErrorAction SilentlyContinue) {
            Log 'Se encontraron restos de una instalación incompleta en pgdata; se limpian.'
            & takeown.exe /F $pgdata /R /A /D Y 2>&1 | Out-Null
            & icacls.exe $pgdata '/grant' '*S-1-5-32-544:(OI)(CI)F' '/T' '/C' '/Q' 2>&1 | Out-Null
            Get-ChildItem $pgdata -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        }
        Log 'Creando la base de datos (initdb)...'
        $pw = Join-Path $DataDir ('cache\pgpw_' + [guid]::NewGuid().ToString('N'))
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
        $x = Invocar-Nativo (Join-Path $bin 'pg_ctl.exe') @('register', '-N', $SvcBd, '-D', $pgdata, '-S', 'auto')
        Log ("pg_ctl: " + $x.Salida)
        if ($x.Codigo -ne 0) { throw "No se pudo registrar el servicio de PostgreSQL (código $($x.Codigo))" }
        Invocar-Nativo 'sc.exe' @('description', $SvcBd, 'Base de datos PostgreSQL de SICOM-MUNI') | Out-Null
    }
    # PostgreSQL se niega a correr con permisos de administrador: la cuenta se fija siempre, sin depender del valor por defecto de pg_ctl
    if ((Get-Service -Name $SvcBd).Status -ne 'Running') {
        $c = Invocar-Nativo 'sc.exe' @('config', $SvcBd, 'obj=', 'NT AUTHORITY\NetworkService')
        Log ('Cuenta del servicio de base de datos: ' + $c.Salida)
    }
    if ((Get-Service -Name $SvcBd).Status -ne 'Running') {
        # en equipos lentos el servicio tarda más que el tiempo de espera de Windows: se sigue esperando abajo
        try { Start-Service -Name $SvcBd -ErrorAction Stop } catch { Log ("Aviso al iniciar el servicio de la base de datos: " + $_.Exception.Message) }
    }
    $listo = $false
    for ($i = 0; $i -lt 90; $i++) {
        $x = Invocar-Nativo (Join-Path $bin 'pg_isready.exe') @('-h', '127.0.0.1', '-p', "$($script:PgPuerto)")
        if ($x.Codigo -eq 0) { $listo = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $listo) {
        Diagnostico-Servicio $SvcBd
        Log ('icacls pgdata: ' + (Invocar-Nativo 'icacls.exe' @($pgdata)).Salida)
        Log ('postgres -C: ' + (Invocar-Nativo (Join-Path $bin 'postgres.exe') @('-D', $pgdata, '-C', 'data_directory')).Salida)
        throw 'La base de datos no inició. Revise C:\ProgramData\SICOM-MUNI\pgdata\log'
    }

    # 6. Rol y base de datos de la aplicación
    $env:PGPASSWORD = $sec.pg_super
    $psql = Join-Path $bin 'psql.exe'
    $base = @('-h', '127.0.0.1', '-p', "$($script:PgPuerto)", '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-q')
    $prueba = Invocar-Nativo $psql ($base + @('-tAc', 'SELECT 1'))
    if ($prueba.Codigo -ne 0 -and $prueba.Salida -match 'password authentication failed|autenticaci') {
        Restablecer-Clave-Postgres $pgdata $bin $sec.pg_super
        $env:PGPASSWORD = $sec.pg_super
        $prueba = Invocar-Nativo $psql ($base + @('-tAc', 'SELECT 1'))
    }
    if ($prueba.Codigo -ne 0) { throw "No se pudo conectar con la base de datos: $($prueba.Salida)" }
    $existeRol = (Invocar-Nativo $psql ($base + @('-tAc', "SELECT 1 FROM pg_roles WHERE rolname='sicom'"))).Salida
    $sql = Join-Path $DataDir ('cache\sicom_' + [guid]::NewGuid().ToString('N') + '.sql')
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
    $plantilla = Get-Content -Raw -Encoding UTF8 (Join-Path $InstallDir 'herramientas\plantillas\servicio.xml.tpl')
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
    Restringir $dirServicio 'RX'
    try { Start-Service -Name $SvcApp -ErrorAction Stop } catch { Log ("Aviso al iniciar el servicio de la aplicación: " + $_.Exception.Message) }

    # 11. Firewall: solo la red local (si Windows Firewall está apagado o lo administra otro antivirus, se avisa y se sigue)
    try {
        Get-NetFirewallRule -DisplayName 'SICOM-MUNI*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName "SICOM-MUNI (puerto $puerto)" -Direction Inbound -Protocol TCP -LocalPort $puerto -Action Allow -Profile Any -RemoteAddress LocalSubnet -ErrorAction Stop | Out-Null
    } catch {
        Log ("AVISO: no se pudo crear la regla del Firewall de Windows (" + $_.Exception.Message + "). Si usa otro antivirus/firewall, permita el puerto TCP $puerto desde la red local.")
        $x = Invocar-Nativo 'netsh.exe' @('advfirewall', 'firewall', 'add', 'rule', "name=SICOM-MUNI (puerto $puerto)", 'dir=in', 'action=allow', 'protocol=TCP', "localport=$puerto", 'remoteip=localsubnet')
        Log ("netsh: " + $x.Salida)
    }

    # 12. Respaldo diario automático (02:00)
    try {
        $accion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}" -Silencioso' -f (Join-Path $InstallDir 'herramientas\respaldar.ps1'))
        $disparador = New-ScheduledTaskTrigger -Daily -At '02:00'
        $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
        Register-ScheduledTask -TaskName 'SICOM-MUNI Respaldo diario' -Action $accion -Trigger $disparador -Principal $principal -Force -ErrorAction Stop | Out-Null
    } catch {
        Log ("AVISO: no se pudo programar el respaldo diario (" + $_.Exception.Message + "). Use «Respaldar ahora» del menú Inicio.")
    }

    # 13. Verificación final
    Log 'Esperando a que el sistema responda...'
    if (-not (Esperar-Url "http://127.0.0.1:$puerto/api/v1/salud" 300)) {
        Diagnostico-Servicio $SvcApp
        Log ('icacls servicio: ' + (Invocar-Nativo 'icacls.exe' @($dirServicio)).Salida)
        throw "El sistema no respondió en 5 minutos. Revise los archivos de $LogDir (SICOM-MUNI-Servicio.*) y el estado del servicio SICOM-MUNI."
    }
    $idEquipo = (Ejecutar-Cli @('id-equipo')).Salida.Trim()
    $lic = Invoke-RestMethod -Uri "http://127.0.0.1:$puerto/api/v1/licencia" -UseBasicParsing
    $nombrePc = $env:COMPUTERNAME
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
    # versión sin tildes para mostrarla en el aviso del instalador
    try { [System.IO.File]::WriteAllText((Join-Path $LogDir 'ultimo-error.txt'), (Sin-Acentos $_.Exception.Message), [System.Text.Encoding]::ASCII) } catch { }
    exit 1
}
finally {
    Remove-Item -Path $Respuestas -Force -ErrorAction SilentlyContinue
}
