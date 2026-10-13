# Funciones comunes de los scripts del instalador (PowerShell 5.1+)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Script:Raiz     = Split-Path -Parent $PSScriptRoot          # carpeta "correspondencia"
$Script:Runtime  = Join-Path $Raiz 'runtime'
$Script:PhpDir   = Join-Path $Runtime 'php'
$Script:DbDir    = Join-Path $Runtime 'mariadb'
$Script:DataDir  = Join-Path $Runtime 'data'
$Script:Puertos  = Join-Path $Runtime 'puertos.json'
$Script:Secretos = Join-Path $Runtime 'secretos.json'
$Script:Log      = Join-Path $PSScriptRoot 'instalacion.log'

function Escribir($texto, $color = 'White') { Write-Host $texto -ForegroundColor $color; try { Add-Content -Path $Script:Log -Value ("[{0}] {1}" -f (Get-Date -Format 's'), $texto) } catch {} }
function Titulo($texto)  { Write-Host ''; Escribir ("=== " + $texto + " ===") 'Cyan' }
function Ok($texto)      { Escribir ("  [OK] " + $texto) 'Green' }
function Aviso($texto)   { Escribir ("  [!]  " + $texto) 'Yellow' }
function Fallo($texto)   { Escribir ("  [X]  " + $texto) 'Red' }

function Buscar-Exe($dir, [string[]]$nombres) {
    foreach ($n in $nombres) {
        $f = Get-ChildItem -Path $dir -Recurse -Filter $n -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($f) { return $f.FullName }
    }
    return $null
}
function Php-Exe    { Join-Path $Script:PhpDir 'php.exe' }
function Db-Server  { Buscar-Exe $Script:DbDir @('mariadbd.exe', 'mysqld.exe') }
function Db-Client  { Buscar-Exe $Script:DbDir @('mariadb.exe', 'mysql.exe') }
function Db-Admin   { Buscar-Exe $Script:DbDir @('mariadb-admin.exe', 'mysqladmin.exe') }
function Db-Dump    { Buscar-Exe $Script:DbDir @('mariadb-dump.exe', 'mysqldump.exe') }
function Db-Install { Buscar-Exe $Script:DbDir @('mariadb-install-db.exe', 'mysql_install_db.exe') }

function Puerto-Libre([int]$inicio) {
    for ($p = $inicio; $p -lt ($inicio + 100); $p++) {
        $ocupado = $false
        try { $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $p); $l.Start(); $l.Stop() } catch { $ocupado = $true }
        if (-not $ocupado) { return $p }
    }
    throw "No se encontró un puerto libre cerca de $inicio."
}
function Puerto-Abierto([int]$p) {
    try { $c = New-Object System.Net.Sockets.TcpClient; $r = $c.BeginConnect('127.0.0.1', $p, $null, $null); $ok = $r.AsyncWaitHandle.WaitOne(500); if ($ok) { $c.EndConnect($r) }; $c.Close(); return $ok } catch { return $false }
}
function Esperar-Puerto([int]$p, [int]$segundos = 60) {
    for ($i = 0; $i -lt $segundos; $i++) { if (Puerto-Abierto $p) { return $true }; Start-Sleep -Seconds 1 }
    return $false
}
function Leer-Json($ruta) { Get-Content -Raw -Path $ruta -Encoding UTF8 | ConvertFrom-Json }
function Escribir-Json($obj, $ruta) { [IO.File]::WriteAllText($ruta, ($obj | ConvertTo-Json), (New-Object System.Text.UTF8Encoding($false))) }

function Clave-Aleatoria([int]$n = 16) {
    $a = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'.ToCharArray()
    -join (1..$n | ForEach-Object { $a[(Get-Random -Maximum $a.Length)] })
}
function Pedir($pregunta, $porDefecto = '') {
    $sufijo = ''; if ($porDefecto) { $sufijo = " [$porDefecto]" }
    $r = Read-Host ($pregunta + $sufijo)
    if ([string]::IsNullOrWhiteSpace($r)) { return $porDefecto }
    return $r.Trim()
}
function Pedir-Clave($pregunta) {
    while ($true) {
        $s1 = Read-Host ($pregunta + ' (mínimo 8 caracteres)') -AsSecureString
        $b1 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s1); $c1 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b1)
        if ($c1.Length -lt 8) { Aviso 'Debe tener al menos 8 caracteres. Intente de nuevo.'; continue }
        $s2 = Read-Host 'Repita la contraseña' -AsSecureString
        $b2 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s2); $c2 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b2)
        if ($c1 -ne $c2) { Aviso 'Las contraseñas no coinciden. Intente de nuevo.'; continue }
        return $c1
    }
}

function Db-Iniciar {
    $cfg = Leer-Json $Script:Puertos
    if (Puerto-Abierto $cfg.db) { return }
    $srv = Db-Server
    if (-not $srv) { throw 'No se encontró MariaDB en runtime\mariadb. Ejecute INSTALAR.bat.' }
    $p = Start-Process -FilePath $srv -ArgumentList ('--defaults-file="' + (Join-Path $Script:Runtime 'my.ini') + '"') -WindowStyle Hidden -PassThru
    Set-Content -Path (Join-Path $Script:Runtime 'mariadb.pid') -Value $p.Id
    if (-not (Esperar-Puerto $cfg.db 60)) { throw 'La base de datos no inició en 60 segundos. Revise runtime\data\*.err' }
}
function Web-Iniciar([switch]$Red) {
    $cfg = Leer-Json $Script:Puertos
    if (Puerto-Abierto $cfg.web) { return }
    $dirIp = '127.0.0.1'; if ($Red) { $dirIp = '0.0.0.0' }
    $argsPhp = @('-c', (Join-Path $Script:PhpDir 'php.ini'), '-S', ("{0}:{1}" -f $dirIp, $cfg.web), '-t', (Join-Path $Script:Raiz 'public'))
    $p = Start-Process -FilePath (Php-Exe) -ArgumentList $argsPhp -WorkingDirectory $Script:Raiz -WindowStyle Hidden -PassThru
    Set-Content -Path (Join-Path $Script:Runtime 'php.pid') -Value $p.Id
    if (-not (Esperar-Puerto $cfg.web 20)) { throw 'El servidor web no inició. Verifique que el puerto no esté en uso.' }
}
function Detener-Todo {
    $s = $null; if (Test-Path $Script:Secretos) { $s = Leer-Json $Script:Secretos }
    $cfg = $null; if (Test-Path $Script:Puertos) { $cfg = Leer-Json $Puertos }
    $pidPhp = Join-Path $Script:Runtime 'php.pid'
    if (Test-Path $pidPhp) { try { Stop-Process -Id ([int](Get-Content $pidPhp)) -Force -ErrorAction SilentlyContinue } catch {}; Remove-Item $pidPhp -Force -ErrorAction SilentlyContinue }
    $adm = Db-Admin
    if ($adm -and $s -and $cfg -and (Puerto-Abierto $cfg.db)) {
        $env:MYSQL_PWD = $s.root
        & $adm '-uroot' '-h127.0.0.1' ("-P" + $cfg.db) 'shutdown' 2>$null | Out-Null
        Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }
    $pidDb = Join-Path $Script:Runtime 'mariadb.pid'
    if (Test-Path $pidDb) { try { $p = Get-Process -Id ([int](Get-Content $pidDb)) -ErrorAction SilentlyContinue; if ($p) { Stop-Process -Id $p.Id -Force } } catch {}; Remove-Item $pidDb -Force -ErrorAction SilentlyContinue }
}
