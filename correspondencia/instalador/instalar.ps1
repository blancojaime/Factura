# Instalador autónomo: descarga PHP y MariaDB portátiles, crea la base de datos y deja el sistema listo.
. "$PSScriptRoot\comun.ps1"
$ProgressPreference = 'SilentlyContinue'   # acelera mucho las descargas
Start-Transcript -Path (Join-Path $PSScriptRoot 'transcripcion.log') -Force | Out-Null
try {
    Clear-Host
    Escribir '========================================================' 'Cyan'
    Escribir '   SISTEMA DE CORRESPONDENCIA - INSTALADOR (1 máquina)' 'Cyan'
    Escribir '========================================================' 'Cyan'
    Escribir 'Este instalador deja todo dentro de la carpeta:'
    Escribir "   $Raiz"
    Escribir 'No modifica Windows ni necesita permisos de administrador.'
    Escribir 'Se descargarán ~120 MB la primera vez (necesita internet).'
    Escribir ''

    if (Test-Path (Join-Path $Raiz 'storage\installed.lock')) {
        Aviso 'El sistema ya está instalado en esta carpeta.'
        Escribir 'Para usarlo, haga doble clic en INICIAR.bat.'
        Escribir 'Para empezar de cero, ejecute primero DESINSTALAR.bat.'
        exit 0
    }

    # ---------- 1. Comprobaciones ----------
    Titulo 'Paso 1 de 6: comprobando su computadora'
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Este instalador requiere Windows de 64 bits.' }
    Ok 'Windows de 64 bits'
    if ($Raiz -match '\\(Temp|Temporary Internet Files)\\' -or $Raiz -match 'Rar\$') { throw 'La carpeta está dentro de un archivo comprimido o temporal. Extraiga TODO el ZIP a una carpeta normal (por ejemplo C:\Correspondencia) y vuelva a intentar.' }
    if ($Raiz -match '[^\x00-\x7F]') { Aviso 'La ruta de la carpeta tiene tildes o eñes. Se recomienda moverla a C:\Correspondencia para evitar problemas.' }
    $unidad = Get-PSDrive -Name ($Raiz.Substring(0, 1)) -ErrorAction SilentlyContinue
    if ($unidad -and $unidad.Free -lt 1GB) { throw 'Hay menos de 1 GB libre en el disco. Libere espacio e intente de nuevo.' }
    Ok 'Espacio en disco suficiente'

    $web = Puerto-Libre 8080; $db = Puerto-Libre 3307
    Ok "Puertos a usar: web $web, base de datos $db"
    New-Item -ItemType Directory -Force -Path $Runtime, (Join-Path $PSScriptRoot 'descargas') | Out-Null

    # ---------- 2. Descargas ----------
    Titulo 'Paso 2 de 6: descargando programas necesarios'
    $descargas = Join-Path $PSScriptRoot 'descargas'
    $phpUrls = @(
        'https://windows.php.net/downloads/releases/archives/php-8.3.12-nts-Win32-vs16-x64.zip',
        'https://windows.php.net/downloads/releases/archives/php-8.3.10-nts-Win32-vs16-x64.zip',
        'https://windows.php.net/downloads/releases/archives/php-8.2.24-nts-Win32-vs16-x64.zip'
    )
    $dbUrls = @(
        'https://archive.mariadb.org/mariadb-10.11.9/winx64-packages/mariadb-10.11.9-winx64.zip',
        'https://archive.mariadb.org/mariadb-10.11.8/winx64-packages/mariadb-10.11.8-winx64.zip',
        'https://archive.mariadb.org/mariadb-10.11.6/winx64-packages/mariadb-10.11.6-winx64.zip'
    )
    function Obtener-Zip($urls, $patron, $etiqueta) {
        $local = Get-ChildItem -Path $descargas -Filter $patron -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($local) { Ok "$etiqueta ya estaba descargado: $($local.Name)"; return $local.FullName }
        foreach ($u in $urls) {
            $dest = Join-Path $descargas ([IO.Path]::GetFileName($u))
            try {
                Escribir "  Descargando $etiqueta ... (puede tardar varios minutos, no cierre esta ventana)"
                Invoke-WebRequest -Uri $u -OutFile $dest -UseBasicParsing -TimeoutSec 1800
                if ((Get-Item $dest).Length -lt 5MB) { throw 'archivo incompleto' }
                Ok "$etiqueta descargado"
                return $dest
            } catch { Aviso "No se pudo con $u ($($_.Exception.Message)); probando otra dirección..."; Remove-Item $dest -Force -ErrorAction SilentlyContinue }
        }
        throw "No se pudo descargar $etiqueta. Compruebe su internet o descargue manualmente un archivo ZIP de $etiqueta (64 bits) y colóquelo en la carpeta instalador\descargas; luego vuelva a ejecutar INSTALAR.bat."
    }
    $phpZip = Obtener-Zip $phpUrls 'php-*-x64.zip' 'PHP'
    $dbZip  = Obtener-Zip $dbUrls  'mariadb-*-winx64.zip' 'MariaDB'

    # ---------- 3. Extracción ----------
    Titulo 'Paso 3 de 6: preparando los programas'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (-not (Test-Path (Php-Exe))) {
        New-Item -ItemType Directory -Force -Path $PhpDir | Out-Null
        [IO.Compression.ZipFile]::ExtractToDirectory($phpZip, $PhpDir)
    }
    if (-not (Db-Server)) {
        New-Item -ItemType Directory -Force -Path $DbDir | Out-Null
        [IO.Compression.ZipFile]::ExtractToDirectory($dbZip, $DbDir)
    }
    if (-not (Test-Path (Php-Exe))) { throw 'PHP no se extrajo correctamente.' }
    if (-not (Db-Server)) { throw 'MariaDB no se extrajo correctamente.' }
    $ini = @"
extension_dir="$($PhpDir -replace '\\','/')/ext"
extension=pdo_mysql
extension=mbstring
extension=fileinfo
extension=zip
extension=openssl
extension=curl
date.timezone=America/La_Paz
upload_max_filesize=12M
post_max_size=14M
memory_limit=256M
display_errors=Off
log_errors=On
error_log="$($Raiz -replace '\\','/')/storage/logs/php_error.log"
"@
    [IO.File]::WriteAllText((Join-Path $PhpDir 'php.ini'), $ini, (New-Object System.Text.UTF8Encoding($false)))
    & (Php-Exe) -c (Join-Path $PhpDir 'php.ini') -v | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'PHP no pudo ejecutarse. Instale "Microsoft Visual C++ Redistributable 2015-2022 (x64)" desde https://aka.ms/vs/17/release/vc_redist.x64.exe y vuelva a ejecutar INSTALAR.bat.' }
    Ok 'PHP listo'
    & (Php-Exe) -c (Join-Path $PhpDir 'php.ini') -m | Out-File (Join-Path $Runtime 'php_modulos.txt')
    $mods = Get-Content (Join-Path $Runtime 'php_modulos.txt')
    foreach ($m in 'pdo_mysql', 'mbstring', 'fileinfo', 'zip', 'dom') { if ($mods -notcontains $m) { throw "A PHP le falta el módulo '$m'." } }
    Ok 'Módulos de PHP verificados'

    # ---------- 4. Base de datos ----------
    Titulo 'Paso 4 de 6: creando la base de datos (local, solo para este equipo)'
    $rootPass = Clave-Aleatoria 20; $appPass = Clave-Aleatoria 20
    $dataFwd = $DataDir -replace '\\', '/'; $baseFwd = ((Split-Path -Parent (Split-Path -Parent (Db-Server))) -replace '\\', '/')
    $myini = @"
[mysqld]
basedir=$baseFwd
datadir=$dataFwd
port=$db
bind-address=127.0.0.1
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
innodb_buffer_pool_size=128M
max_connections=50
"@
    [IO.File]::WriteAllText((Join-Path $Runtime 'my.ini'), $myini, (New-Object System.Text.UTF8Encoding($false)))
    Escribir-Json @{ web = $web; db = $db } $Puertos
    Escribir-Json @{ root = $rootPass; app = $appPass } $Secretos
    $inst = Db-Install
    if (-not $inst) { throw 'No se encontró mariadb-install-db.exe dentro de MariaDB.' }
    & $inst ("--datadir=$DataDir") ("--password=$rootPass") ("--port=$db") | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo inicializar la base de datos.' }
    Db-Iniciar
    Ok 'Servidor de base de datos iniciado'
    $cli = Db-Client
    $env:MYSQL_PWD = $rootPass
    & $cli '-uroot' '-h127.0.0.1' "-P$db" '-e' "CREATE DATABASE IF NOT EXISTS correspondencia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'corr'@'localhost' IDENTIFIED BY '$appPass'; GRANT ALL ON correspondencia.* TO 'corr'@'localhost'; FLUSH PRIVILEGES;"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la base de datos.' }
    Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
    Ok 'Base de datos "correspondencia" creada'

    # ---------- 5. Datos de la institución ----------
    Titulo 'Paso 5 de 6: datos de su institución (responda y pulse Enter)'
    $entidad = ''; while (-not $entidad) { $entidad = Pedir 'Nombre de la entidad (ej. Gobierno Autónomo Municipal de ...)' }
    $sigla = ''; while (-not $sigla) { $sigla = (Pedir 'Sigla corta, sin espacios (ej. GAMX)').ToUpper() -replace '[^A-Z0-9]', '' }
    $adminNombre = Pedir 'Su nombre completo (administrador)' 'Administrador'
    $adminLogin = Pedir 'Usuario del administrador' 'admin'
    $adminPass = Pedir-Clave 'Contraseña del administrador'
    $env:CORR_DB_HOST = '127.0.0.1'; $env:CORR_DB_PORT = "$db"; $env:CORR_DB_NAME = 'correspondencia'; $env:CORR_DB_USER = 'corr'; $env:CORR_DB_PASS = $appPass
    $env:CORR_ENTIDAD = $entidad; $env:CORR_SIGLA = $sigla; $env:CORR_ADMIN_LOGIN = $adminLogin; $env:CORR_ADMIN_PASS = $adminPass; $env:CORR_ADMIN_NOMBRE = $adminNombre
    Push-Location $Raiz
    & (Php-Exe) -c (Join-Path $PhpDir 'php.ini') 'bin\install.php'
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Falló la creación de tablas del sistema.' }
    Ok 'Tablas y administrador creados'
    $excel = Join-Path $Raiz 'database\Cargos_y_Oficinas_GAM.xlsx'
    if (Test-Path $excel) {
        $r = Pedir '¿Cargar las oficinas y cargos del archivo Cargos_y_Oficinas_GAM.xlsx? (S/N)' 'S'
        if ($r -match '^[sS]') {
            & (Php-Exe) -c (Join-Path $PhpDir 'php.ini') 'bin\importar.php' $excel (Join-Path $Raiz 'CLAVES_TEMPORALES.csv')
            if ($LASTEXITCODE -eq 0) { Ok 'Cargos importados. Claves temporales en CLAVES_TEMPORALES.csv (imprímalo y guárdelo en lugar seguro)' } else { Aviso 'No se pudo importar; podrá hacerlo luego desde Administración > Importar cargos.' }
        }
    }
    Pop-Location
    foreach ($v in 'CORR_DB_PASS', 'CORR_ADMIN_PASS') { Remove-Item "Env:$v" -ErrorAction SilentlyContinue }

    # ---------- 6. Arranque y acceso directo ----------
    Titulo 'Paso 6 de 6: iniciando el sistema'
    Web-Iniciar
    Ok "Sistema funcionando en http://localhost:$web/"
    try {
        $ws = New-Object -ComObject WScript.Shell
        $lnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Correspondencia.lnk'))
        $lnk.TargetPath = (Join-Path $Raiz 'INICIAR.bat'); $lnk.WorkingDirectory = $Raiz; $lnk.Description = 'Sistema de Correspondencia'; $lnk.Save()
        Ok 'Acceso directo "Correspondencia" creado en el Escritorio'
    } catch { Aviso 'No se pudo crear el acceso directo; use INICIAR.bat de la carpeta.' }
    Start-Process "http://localhost:$web/"
    Escribir ''
    Escribir '========================================================' 'Green'
    Escribir '   INSTALACIÓN TERMINADA' 'Green'
    Escribir '========================================================' 'Green'
    Escribir "Dirección:  http://localhost:$web/"
    Escribir "Usuario:    $adminLogin"
    Escribir 'Para volver a usarlo otro día: doble clic en "Correspondencia" (Escritorio) o INICIAR.bat'
    Escribir 'Para apagarlo: DETENER.bat      Para copia de seguridad: RESPALDAR.bat'
    exit 0
}
catch {
    Fallo $_.Exception.Message
    Escribir 'Corrija el problema y vuelva a ejecutar INSTALAR.bat (continuará donde quedó).' 'Yellow'
    try { Detener-Todo } catch {}
    exit 1
}
finally { try { Stop-Transcript | Out-Null } catch {} }
