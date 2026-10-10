# SICOM-MUNI - modo de PRUEBA sin Docker (Windows). Usa SQLite en un archivo local.
# Instala (si faltan) Python y Node con winget, prepara el sistema y lo abre en el navegador.
$ErrorActionPreference = 'Continue'   # los avisos de pip/npm (stderr) no deben detener el script
$root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$local = Join-Path $root '.local'
New-Item -ItemType Directory -Force -ErrorAction Stop -Path $local | Out-Null
$logs = Join-Path $local 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Paso($t) { Write-Host ''; Write-Host "== $t" -ForegroundColor Cyan }
function Refrescar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Esta-Listo($url) {
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3; return ($r.StatusCode -lt 500) } catch { return $false }
}
function Instalar-Winget($id, $nombre) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Su Windows no tiene 'winget'. Instale $nombre manualmente (Python 3.12 desde python.org marcando 'Add python.exe to PATH'; Node.js LTS desde nodejs.org) y vuelva a ejecutar este archivo."
    }
    Write-Host "Instalando $nombre (puede pedir permiso de administrador; acepte)..."
    winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements
    Refrescar-Path
}
function Get-PythonExe {
    $cands = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try { $p = & py -3 -c "import sys;print(sys.executable)" 2>$null; if ($p) { $cands += $p } } catch { }
    }
    $pt = Get-Command python -ErrorAction SilentlyContinue
    if ($pt -and $pt.Source -notlike '*WindowsApps*') { $cands += $pt.Source }
    $base = Join-Path $env:LocalAppData 'Programs\Python'
    if (Test-Path $base) {
        foreach ($d in Get-ChildItem $base -Directory) {
            $e = Join-Path $d.FullName 'python.exe'
            if (Test-Path $e) { $cands += $e }
        }
    }
    foreach ($c in $cands) {
        try {
            $ok = & $c -c "import sys;print(1 if (3,10) <= sys.version_info[:2] < (3,14) else 0)" 2>$null
            if ("$ok".Trim() -eq '1') { return $c }
        } catch { }
    }
    return $null
}
function Get-NodeExe {
    $n = Get-Command node -ErrorAction SilentlyContinue
    if (-not $n) { return $null }
    try {
        $v = (& $n.Source -v).TrimStart('v').Split('.')[0]
        if ([int]$v -ge 18) { return $n.Source }
    } catch { }
    return $null
}

try {
    Write-Host '============================================================'
    Write-Host '  SICOM-MUNI - modo de PRUEBA sin Docker'
    Write-Host '============================================================'

    if ((Esta-Listo 'http://127.0.0.1:3000/login') -and (Esta-Listo 'http://127.0.0.1:8000/api/v1/salud')) {
        Write-Host 'El sistema ya estaba encendido. Abriendo el navegador...'
        Start-Process 'http://localhost:3000'
        Start-Sleep -Seconds 4
        exit 0
    }

    Paso '1/6  Comprobando Python'
    $py = Get-PythonExe
    if (-not $py) { Instalar-Winget 'Python.Python.3.12' 'Python 3.12'; $py = Get-PythonExe }
    if (-not $py) { throw 'No se pudo encontrar Python. Cierre esta ventana, abra el archivo de nuevo; si persiste, instale Python 3.12 desde python.org.' }
    Write-Host "Python: $py"

    Paso '2/6  Comprobando Node.js'
    $node = Get-NodeExe
    if (-not $node) { Instalar-Winget 'OpenJS.NodeJS.LTS' 'Node.js LTS'; $node = Get-NodeExe }
    if (-not $node) { throw 'No se pudo encontrar Node.js. Cierre esta ventana, abra el archivo de nuevo; si persiste, instale Node.js LTS desde nodejs.org.' }
    Write-Host "Node: $node"

    Paso '3/6  Preparando el servidor (Python)'
    $venv = Join-Path $local 'venv'
    $venvpy = Join-Path $venv 'Scripts\python.exe'
    if (-not (Test-Path $venvpy)) { & $py -m venv $venv; if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de Python.' } }
    $req = Join-Path $root 'backend\requirements.txt'
    $marca = Join-Path $local 'deps_py.txt'
    $hash = (Get-FileHash $req -Algorithm SHA256).Hash
    if ((-not (Test-Path $marca)) -or ((Get-Content $marca -Raw).Trim() -ne $hash)) {
        Write-Host 'Instalando componentes de Python (la primera vez tarda unos minutos)...'
        & $venvpy -m pip install --disable-pip-version-check --upgrade pip | Out-Null
        & $venvpy -m pip install --disable-pip-version-check -r $req
        if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de los componentes de Python.' }
        Set-Content -Path $marca -Value $hash
    }

    # Variables del servidor (SQLite local)
    $dbFile = (Join-Path $local 'sicom.db') -replace '\\', '/'
    $env:DATABASE_URL = "sqlite:///$dbFile"
    $env:LOCAL_STORAGE_PATH = Join-Path $local 'storage'
    $env:PUBLIC_BASE_URL = 'http://localhost:3000'
    $env:COOKIE_SECURE = 'false'
    $secretFile = Join-Path $local 'secret.txt'
    if (-not (Test-Path $secretFile)) {
        $chars = (48..57) + (65..90) + (97..122)
        Set-Content -Path $secretFile -Value (-join ($chars | Get-Random -Count 64 | ForEach-Object { [char]$_ }))
    }
    $env:SECRET_KEY = (Get-Content $secretFile -Raw).Trim()
    if ((-not $env:WEASYPRINT_DLL_DIRECTORIES) -and (Test-Path 'C:\msys64\mingw64\bin')) { $env:WEASYPRINT_DLL_DIRECTORIES = 'C:\msys64\mingw64\bin' }

    $primeraVez = -not (Test-Path (Join-Path $local 'sicom.db'))
    Push-Location (Join-Path $root 'backend')
    if ($primeraVez) {
        Write-Host 'Creando la base de datos y cargando los usuarios de demostracion...'
        & $venvpy -m app.seeds
        if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Fallo la carga de datos de demostracion.' }
    }
    & $venvpy -c "import weasyprint" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'AVISO: no se encontro el motor de PDF (WeasyPrint). Los documentos se mostraran como paginas HTML imprimibles (Ctrl+P > Guardar como PDF).' -ForegroundColor Yellow
        Write-Host '       Para generar PDF reales ejecute INSTALAR-SOPORTE-PDF.bat (opcional).' -ForegroundColor Yellow
    }
    Pop-Location

    Paso '4/6  Preparando la pantalla web (Node)'
    $front = Join-Path $root 'frontend'
    $env:BACKEND_URL = 'http://127.0.0.1:8000'
    $env:NEXT_TELEMETRY_DISABLED = '1'
    Push-Location $front
    $lock = Join-Path $front 'package-lock.json'
    $marcaN = Join-Path $local 'deps_node.txt'
    $hashN = (Get-FileHash $lock -Algorithm SHA256).Hash
    if ((-not (Test-Path (Join-Path $front 'node_modules'))) -or (-not (Test-Path $marcaN)) -or ((Get-Content $marcaN -Raw).Trim() -ne $hashN)) {
        Write-Host 'Instalando componentes de Node (la primera vez tarda unos minutos)...'
        & npm ci --no-audit --no-fund --loglevel=error
        if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Fallo la instalacion de los componentes de Node.' }
        Set-Content -Path $marcaN -Value $hashN
    }
    $buildId = Join-Path $front '.next\BUILD_ID'
    $recompilar = -not (Test-Path $buildId)
    if (-not $recompilar) {
        $ultimo = (Get-ChildItem (Join-Path $front 'src') -Recurse -File | Measure-Object -Property LastWriteTime -Maximum).Maximum
        if ($ultimo -gt (Get-Item $buildId).LastWriteTime) { $recompilar = $true }
    }
    if ($recompilar) {
        Write-Host 'Compilando la pantalla web (1 a 3 minutos)...'
        & npm run build
        if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Fallo la compilacion de la pantalla web.' }
    }
    Pop-Location

    Paso '5/6  Encendiendo el sistema'
    $pidFile = Join-Path $local 'pids.txt'
    $be = Start-Process -FilePath $venvpy -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
        -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden -PassThru -ErrorAction Stop `
        -RedirectStandardOutput (Join-Path $logs 'backend.log') -RedirectStandardError (Join-Path $logs 'backend.err.log')
    $fe = Start-Process -FilePath $node -ArgumentList 'node_modules\next\dist\bin\next', 'start', '-p', '3000' `
        -WorkingDirectory $front -WindowStyle Hidden -PassThru -ErrorAction Stop `
        -RedirectStandardOutput (Join-Path $logs 'frontend.log') -RedirectStandardError (Join-Path $logs 'frontend.err.log')
    Set-Content -Path $pidFile -Value @($be.Id, $fe.Id)

    Paso '6/6  Esperando a que responda'
    $ok = $false
    for ($i = 0; $i -lt 60; $i++) {
        if ((Esta-Listo 'http://127.0.0.1:8000/api/v1/salud') -and (Esta-Listo 'http://127.0.0.1:3000/login')) { $ok = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ok) { throw "El sistema no respondio. Revise los archivos de la carpeta $logs y envielos a soporte." }

    Start-Process 'http://localhost:3000'
    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Green
    Write-Host '  LISTO. Abra: http://localhost:3000' -ForegroundColor Green
    Write-Host '  Usuario: solicitante    Clave: Sicom#2026Demo'
    Write-Host '  (otros usuarios: presupuesto, contrataciones, rpa, recepcion, admin)'
    Write-Host '  Para apagar: DETENER-SIN-DOCKER.bat'
    Write-Host '============================================================' -ForegroundColor Green
}
catch {
    Write-Host ''
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Si necesita ayuda, envie una captura de esta ventana y los archivos de $logs"
}
Read-Host 'Presione Enter para cerrar esta ventana'
