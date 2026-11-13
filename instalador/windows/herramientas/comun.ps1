# Funciones comunes de las herramientas de SICOM-MUNI (se cargan con ". comun.ps1")
$ErrorActionPreference = 'Stop'
$script:InstallDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script:DataDir    = Join-Path $env:ProgramData 'SICOM-MUNI'
$script:ConfigDir  = Join-Path $DataDir 'config'
$script:LogDir     = Join-Path $DataDir 'logs'
$script:PgPuerto   = 54329
$script:SvcApp     = 'SICOM-MUNI'
$script:SvcBd      = 'SICOM-MUNI-BD'

function Escribir-Log([string]$mensaje, [string]$archivo = 'herramientas.log') {
    $linea = '{0:yyyy-MM-dd HH:mm:ss}  {1}' -f (Get-Date), $mensaje
    try {
        New-Item -ItemType Directory -Force -Path $script:LogDir | Out-Null
        Add-Content -Path (Join-Path $script:LogDir $archivo) -Value $linea -Encoding UTF8
    } catch { }
    Write-Host $mensaje
}

function Es-Administrador {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Si no es administrador, vuelve a abrir el mismo script con permisos de administrador.
function Exigir-Administrador([string]$ruta, [string[]]$argumentos = @()) {
    if (Es-Administrador) { return }
    $lista = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $ruta)) + $argumentos
    Start-Process -FilePath 'powershell.exe' -ArgumentList $lista -Verb RunAs
    exit 0
}

function Leer-Env {
    $mapa = @{}
    $ruta = Join-Path $script:ConfigDir '.env'
    if (Test-Path $ruta) {
        foreach ($l in Get-Content $ruta -Encoding UTF8) {
            if ($l -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.*)$') { $mapa[$Matches[1]] = $Matches[2] }
        }
    }
    return $mapa
}

function Datos-Bd {
    $e = Leer-Env
    if ($e['DATABASE_URL'] -match '^postgresql\+psycopg://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)$') {
        return @{ Usuario = $Matches[1]; Clave = $Matches[2]; Host = $Matches[3]; Puerto = $Matches[4]; Base = $Matches[5] }
    }
    throw 'No se pudo leer la configuración de la base de datos (.env)'
}

function Ip-Local {
    try {
        $ruta = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction Stop | Sort-Object RouteMetric | Select-Object -First 1
        $ip = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $ruta.InterfaceIndex -ErrorAction Stop |
              Where-Object { $_.IPAddress -notlike '169.254.*' } | Select-Object -First 1
        if ($ip) { return $ip.IPAddress }
    } catch { }
    try {
        $ip = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Select-Object -First 1
        if ($ip) { return $ip.IPAddress }
    } catch { }
    return '127.0.0.1'
}

function Esperar-Url([string]$url, [int]$segundos = 90) {
    $limite = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $limite) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 5
            if ($r.StatusCode -lt 500) { return $true }
        } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Variables-De-Motor {
    # Entorno necesario para ejecutar Python (PDF, fuentes, configuración)
    $env:SICOM_GTK_DIR = Join-Path $script:InstallDir 'gtk\bin'
    $env:FONTCONFIG_FILE = Join-Path $script:ConfigDir 'fonts.conf'
    $env:PYTHONUTF8 = '1'
    $env:PATH = (Join-Path $script:InstallDir 'gtk\bin') + ';' + $env:PATH
}

# Ejecuta un programa externo sin que los avisos por stderr detengan el script (PowerShell 5.1).
function Invocar-Nativo {
    param([string]$Exe, [string[]]$Argumentos = @())
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $salida = & $Exe @Argumentos 2>&1 | ForEach-Object { "$_" }
        $codigo = $LASTEXITCODE
    } finally { $ErrorActionPreference = $anterior }
    return [pscustomobject]@{ Codigo = $codigo; Salida = (($salida | Out-String).Trim()) }
}

# Escribe texto en UTF-8 SIN marca BOM (los archivos .env deben leerse limpios).
function Escribir-Archivo([string]$ruta, [string]$texto) {
    [System.IO.File]::WriteAllText($ruta, $texto, (New-Object System.Text.UTF8Encoding($false)))
}

function Ejecutar-Cli([string[]]$argumentos) {
    Variables-De-Motor
    Push-Location $script:ConfigDir
    try {
        $py = Join-Path $script:InstallDir 'python\python.exe'
        $r = Invocar-Nativo $py (@('-m', 'app.cli') + $argumentos)
        return @{ Codigo = $r.Codigo; Salida = $r.Salida }
    } finally { Pop-Location }
}
