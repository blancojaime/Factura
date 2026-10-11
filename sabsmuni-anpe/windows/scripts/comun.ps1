# Funciones compartidas de los instaladores. Mensajes en ASCII a proposito (consolas de Windows sin UTF-8).
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$EsWindows = ($env:OS -eq 'Windows_NT')

$Win     = Split-Path -Parent $PSScriptRoot            # ...\sabsmuni-anpe\windows
$Proy    = Split-Path -Parent $Win                      # ...\sabsmuni-anpe
$Runtime = Join-Path $Win 'runtime'                     # node + postgresql portables
$Datos   = Join-Path $Win 'datos'                       # base de datos, documentos, logs, respaldos
$Logs    = Join-Path $Datos 'logs'
$PgData  = Join-Path $Datos 'pgdata'
$Storage = Join-Path $Datos 'storage'
$EnvFile = Join-Path $Datos 'anpe.env'
$PidFile = Join-Path $Datos 'procesos.json'
$Backend = Join-Path $Proy 'backend'
$Frontend= Join-Path $Proy 'frontend'

# Versiones fijadas (probadas con este sistema)
$NodeVersion = '22.22.0'
$PgPackage   = if ($EsWindows) { '@embedded-postgres/windows-x64@16.14.0-beta.17' } else { '@embedded-postgres/linux-x64@16.14.0-beta.17' }

$PuertoWeb = 3000
$PuertoApi = 4000
$PuertoPg  = 5433

function Paso($t)  { Write-Host ''; Write-Host "==> $t" -ForegroundColor Cyan }
function Ok($t)    { Write-Host "    [OK] $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "    [!]  $t" -ForegroundColor Yellow }
function Falla($t) { throw $t }

function Dir-Node { Join-Path $Runtime 'node' }
function Exe-Node { if ($EsWindows) { Join-Path (Dir-Node) 'node.exe' } else { Join-Path (Dir-Node) 'bin/node' } }
function Js-Npm   { if ($EsWindows) { Join-Path (Dir-Node) 'node_modules\npm\bin\npm-cli.js' } else { Join-Path (Dir-Node) 'lib/node_modules/npm/bin/npm-cli.js' } }
function Dir-Pg   { Join-Path $Runtime 'pgsql/package/native' }
function Exe-Pg($n) { $f = if ($EsWindows) { "$n.exe" } else { $n }; Join-Path (Dir-Pg) "bin/$f" }

function Preparar-Path {
    $sep = [IO.Path]::PathSeparator
    $nodeBin = if ($EsWindows) { Dir-Node } else { Join-Path (Dir-Node) 'bin' }
    $env:PATH = "$nodeBin$sep$env:PATH"
}

# Ejecuta un programa externo y falla con un mensaje claro si devuelve error.
function Ejecutar([string]$exe, [string[]]$argumentos, [string]$cwd = $Proy, [string]$que = '') {
    Push-Location $cwd
    try {
        & $exe @argumentos
        if ($LASTEXITCODE -ne 0) { Falla "Fallo el comando '$que' (codigo $LASTEXITCODE). Revise el mensaje de arriba y el archivo datos\logs\instalacion.log" }
    } finally { Pop-Location }
}
function Npm([string[]]$argumentos, [string]$cwd, [string]$que) { Ejecutar (Exe-Node) (@((Js-Npm)) + $argumentos) $cwd $que }

function Descargar([string]$url, [string]$destino) {
    if (Test-Path $destino) { Remove-Item $destino -Force }
    Write-Host "    Descargando $url"
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($EsWindows -and $curl) { & $curl.Source -L --fail --retry 3 -o $destino $url; if ($LASTEXITCODE -ne 0) { Falla "No se pudo descargar $url (revise su conexion a internet o el proxy de la red)." } }
    else { Invoke-WebRequest -Uri $url -OutFile $destino -UseBasicParsing }
}

function Extraer([string]$archivo, [string]$destino) {
    New-Item -ItemType Directory -Force -Path $destino | Out-Null
    $tar = Get-Command tar -ErrorAction SilentlyContinue
    if ($tar) { & $tar.Source -xf $archivo -C $destino; if ($LASTEXITCODE -ne 0) { Falla "No se pudo extraer $archivo" } }
    else { Expand-Archive -Path $archivo -DestinationPath $destino -Force }
}

function Texto-Aleatorio([int]$bytes) {
    $b = New-Object byte[] $bytes
    $r = [Security.Cryptography.RandomNumberGenerator]::Create(); $r.GetBytes($b); $r.Dispose()
    ($b | ForEach-Object { $_.ToString('x2') }) -join ''
}

function Cargar-Entorno {
    if (-not (Test-Path $EnvFile)) { Falla 'Falta datos\anpe.env: ejecute primero 1-INSTALAR.bat' }
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([A-Z0-9_]+)=(.*)$') { Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2] }
    }
}

function Pg-Corriendo {
    $pgctl = Exe-Pg 'pg_ctl'
    if (-not (Test-Path (Join-Path $PgData 'PG_VERSION'))) { return $false }
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'   # PowerShell 5.1 trata la salida de error de un programa como error fatal
    try { & $pgctl -D $PgData status *> $null; return ($LASTEXITCODE -eq 0) }
    catch { return $false }
    finally { $ErrorActionPreference = $anterior }
}

function Pg-Iniciar {
    if (Pg-Corriendo) { return }
    $opc = "-p $PuertoPg -c listen_addresses=127.0.0.1"
    if (-not $EsWindows) { $opc += " -c unix_socket_directories=$Datos" }
    New-Item -ItemType Directory -Force -Path $Logs | Out-Null
    Ejecutar (Exe-Pg 'pg_ctl') @('-D', $PgData, '-l', (Join-Path $Logs 'postgres.log'), '-w', '-t', '60', '-o', $opc, 'start') $Proy 'iniciar PostgreSQL'
}
function Pg-Detener {
    if (Pg-Corriendo) { & (Exe-Pg 'pg_ctl') -D $PgData -m fast -w stop | Out-Null }
}

function Esperar-Url([string]$url, [int]$segundos) {
    $limite = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $limite) {
        try { $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5; if ($r.StatusCode -lt 500) { return $true } } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Detener-Aplicacion {
    if (Test-Path $PidFile) {
        $p = Get-Content $PidFile -Raw | ConvertFrom-Json
        foreach ($id in @($p.backend, $p.frontend)) {
            if ($id) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
        }
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
    if ($EsWindows) {
        foreach ($puerto in @($PuertoWeb, $PuertoApi)) {
            Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue |
                ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        }
    }
}
