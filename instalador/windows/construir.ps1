# Prepara el contenido del instalador de Windows en _stage (se ejecuta en GitHub Actions, en Windows).
# Requisitos previos: frontend exportado en sicom-muni/frontend/out, DLL de GTK en _gtk, Python 3.12 en el PATH.
param(
    [string]$Version = '2.0.0',
    [string]$PythonEmbed = '3.12.8',
    [string]$Postgres = '16.4-1'
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$aqui = $PSScriptRoot
$raiz = (Resolve-Path (Join-Path $aqui '..\..')).Path
$stage = Join-Path $aqui '_stage'
$tmp = Join-Path $aqui '_tmp'

function Paso([string]$t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Bajar([string]$url, [string]$destino) {
    Write-Host "Descargando $url"
    Invoke-WebRequest -Uri $url -OutFile $destino -UseBasicParsing -MaximumRetryCount 5 -RetryIntervalSec 8
    if (-not (Test-Path $destino) -or (Get-Item $destino).Length -lt 100000) { throw "Descarga incompleta: $url" }
}

Remove-Item -Recurse -Force $stage, $tmp -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $stage, $tmp | Out-Null
foreach ($d in 'python', 'site-packages', 'backend', 'web', 'pgsql', 'gtk', 'fonts', 'herramientas', 'prerequisitos', 'docs') { New-Item -ItemType Directory -Force -Path (Join-Path $stage $d) | Out-Null }

Paso 'Pantalla web (exportada)'
$out = Join-Path $raiz 'sicom-muni\frontend\out'
if (-not (Test-Path (Join-Path $out 'index.html'))) { throw "Falta la pantalla web exportada en $out (npm run build con NEXT_EXPORT=1)" }
Copy-Item -Recurse -Force (Join-Path $out '*') (Join-Path $stage 'web')

Paso "Python $PythonEmbed (portátil)"
$zipPy = Join-Path $tmp 'python.zip'
Bajar "https://www.python.org/ftp/python/$PythonEmbed/python-$PythonEmbed-embed-amd64.zip" $zipPy
Expand-Archive -Path $zipPy -DestinationPath (Join-Path $stage 'python') -Force
$pth = Get-ChildItem (Join-Path $stage 'python') -Filter 'python*._pth' | Select-Object -First 1
$zipStd = (Get-ChildItem (Join-Path $stage 'python') -Filter 'python*.zip' | Select-Object -First 1).Name
Set-Content -Path $pth.FullName -Encoding ASCII -Value @($zipStd, '.', '..\site-packages', '..\backend', 'import site')

Paso 'Dependencias de Python'
$sp = Join-Path $stage 'site-packages'
& python -m pip install --no-cache-dir --only-binary=:all: --target $sp -r (Join-Path $raiz 'sicom-muni\backend\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip install falló' }

Paso 'Código del sistema'
$be = Join-Path $stage 'backend'
Copy-Item -Recurse -Force (Join-Path $raiz 'sicom-muni\backend\app') (Join-Path $be 'app')
Copy-Item -Recurse -Force (Join-Path $raiz 'sicom-muni\backend\alembic') (Join-Path $be 'alembic')
Copy-Item -Force (Join-Path $raiz 'sicom-muni\backend\alembic.ini') $be
Get-ChildItem $be -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
& python -m compileall -q -j 0 $sp $be
if ($LASTEXITCODE -ne 0) { throw 'compileall falló' }

Paso "PostgreSQL $Postgres"
$zipPg = Join-Path $tmp 'pg.zip'
Bajar "https://get.enterprisedb.com/postgresql/postgresql-$Postgres-windows-x64-binaries.zip" $zipPg
Expand-Archive -Path $zipPg -DestinationPath $tmp -Force
$pgOrigen = Join-Path $tmp 'pgsql'
foreach ($d in 'bin', 'lib', 'share') { Copy-Item -Recurse -Force (Join-Path $pgOrigen $d) (Join-Path $stage "pgsql\$d") }
Get-ChildItem (Join-Path $stage 'pgsql') -Recurse -Include '*.pdb', '*.lib', '*.a' | Remove-Item -Force -ErrorAction SilentlyContinue

Paso 'Librerías gráficas (Pango) y fuentes'
$gtk = Join-Path $aqui '_gtk'
if (-not (Test-Path (Join-Path $gtk 'bin\libpango-1.0-0.dll'))) { throw "Faltan las DLL de Pango en $gtk (paso MSYS2)" }
Copy-Item -Recurse -Force (Join-Path $gtk 'bin') (Join-Path $stage 'gtk\bin')
Copy-Item -Force (Join-Path $gtk 'fonts\*') (Join-Path $stage 'fonts')

Paso 'Servicio de Windows (WinSW) y requisitos'
Bajar 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe' (Join-Path $stage 'herramientas\winsw.exe')
Bajar 'https://aka.ms/vs/17/release/vc_redist.x64.exe' (Join-Path $stage 'prerequisitos\vc_redist.x64.exe')

Paso 'Herramientas de administración y documentos'
Copy-Item -Recurse -Force (Join-Path $aqui 'herramientas\*') (Join-Path $stage 'herramientas')
Copy-Item -Recurse -Force (Join-Path $aqui 'plantillas') (Join-Path $stage 'herramientas\plantillas')
foreach ($m in 'MANUAL_INSTALACION_RED_LOCAL.docx') {
    $f = Join-Path $raiz "sicom-muni\docs\$m"
    if (Test-Path $f) { Copy-Item -Force $f (Join-Path $stage 'docs') }
}
Copy-Item -Force (Join-Path $aqui 'LEEME.txt') (Join-Path $stage 'docs')

Paso 'Prueba del paquete (Python, módulos, licencias y PDF con QR)'
$py = Join-Path $stage 'python\python.exe'
$fuentes = (Get-Content -Raw (Join-Path $aqui 'plantillas\fonts.conf.tpl')).Replace('@INSTALL@', $stage).Replace('@DATA@', $tmp)
Set-Content -Path (Join-Path $tmp 'fonts.conf') -Value $fuentes -Encoding UTF8
$env:SICOM_GTK_DIR = Join-Path $stage 'gtk\bin'
$env:FONTCONFIG_FILE = Join-Path $tmp 'fonts.conf'
$env:PATH = "$($env:SICOM_GTK_DIR);$env:PATH"
$env:PYTHONUTF8 = '1'
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $tmp 'prueba.db') -replace '\\', '/')
$env:LOCAL_STORAGE_PATH = Join-Path $tmp 'archivos'
$env:SICOM_ENTIDAD = 'Prueba'; $env:SICOM_ADMIN_USUARIO = 'admin'; $env:SICOM_ADMIN_CLAVE = 'Prueba#Segura2026'
Push-Location $tmp
try {
    & $py -c "import fastapi, uvicorn, sqlalchemy, alembic, psycopg, argon2, cryptography, PIL, qrcode, jwt, openpyxl, weasyprint, app.main; print('modulos OK')"
    if ($LASTEXITCODE -ne 0) { throw 'Faltan módulos de Python en el paquete' }
    & $py -m app.cli inicializar
    if ($LASTEXITCODE -ne 0) { throw 'app.cli inicializar falló' }
    & $py -m app.cli id-equipo
    if ($LASTEXITCODE -ne 0) { throw 'app.cli id-equipo falló' }
    & $py -m app.cli probar-pdf (Join-Path $tmp 'prueba.pdf')
    if ($LASTEXITCODE -ne 0) { throw 'El motor de PDF (Pango) no funciona dentro del paquete' }
    $cab = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes((Join-Path $tmp 'prueba.pdf')), 0, 5)
    if ($cab -ne '%PDF-') { throw 'El PDF de prueba es inválido' }
    Write-Host 'PDF de prueba generado correctamente.'
} finally { Pop-Location }

Paso 'Resumen'
$mb = [math]::Round(((Get-ChildItem $stage -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB)
Write-Host "Contenido del instalador: $mb MB (sin comprimir)"
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
