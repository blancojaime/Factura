# Instalador SIN Docker y SIN administrador. Se puede ejecutar varias veces: retoma donde quedo.
. "$PSScriptRoot\comun.ps1"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
Start-Transcript -Path (Join-Path $Logs 'instalacion.log') -Append | Out-Null
$exito = $false
try {
    Write-Host '=============================================================' -ForegroundColor Cyan
    Write-Host ' SABSMUNI-ANPE - Instalacion de prueba (sin Docker)' -ForegroundColor Cyan
    Write-Host ' Tarda 15 a 40 minutos la primera vez (descargas + compilacion).' -ForegroundColor Cyan
    Write-Host '=============================================================' -ForegroundColor Cyan

    Paso '0/8 Verificando requisitos'
    if ($Proy -match '\s') { Falla "La carpeta '$Proy' tiene espacios. Mueva la carpeta sabsmuni-anpe a C:\sabsmuni-anpe y vuelva a ejecutar." }
    if ($Proy -match '[^\x00-\x7F]') { Falla "La ruta '$Proy' tiene tildes o letras especiales. Mueva la carpeta sabsmuni-anpe a C:\sabsmuni-anpe y vuelva a ejecutar." }
    if ($Proy.Length -gt 60) { Aviso 'La ruta es larga; si hay errores de "ruta demasiado larga", mueva la carpeta a C:\sabsmuni-anpe.' }
    if ($EsWindows) {
        $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if ($admin) { Falla 'No ejecute este instalador como Administrador (PostgreSQL se niega a funcionar asi). Cierre esta ventana y haga doble clic normal en 1-INSTALAR.bat' }
        $libre = (Get-PSDrive -Name ($Proy.Substring(0,1)) -ErrorAction SilentlyContinue).Free
        if ($libre -and $libre -lt 4GB) { Falla 'Hay menos de 4 GB libres en el disco. Libere espacio e intente de nuevo.' }
    }
    if (-not (Test-Path (Join-Path $Backend 'package.json'))) { Falla "No encuentro la carpeta backend en '$Proy'. Ejecute el instalador desde dentro de la carpeta sabsmuni-anpe\windows." }
    Ok "Carpeta: $Proy"

    New-Item -ItemType Directory -Force -Path $Runtime, $Datos, $Storage, (Join-Path $Runtime '_descargas') | Out-Null
    Preparar-Path

    Paso '1/8 Node.js portable'
    if (-not (Test-Path (Exe-Node))) {
        if (-not $EsWindows) { Falla 'En Linux/Mac coloque Node 22 en windows/runtime/node (solo uso de desarrollo).' }
        $zip = Join-Path $Runtime "_descargas\node-$NodeVersion.zip"
        Descargar "https://nodejs.org/dist/v$NodeVersion/node-v$NodeVersion-win-x64.zip" $zip
        Extraer $zip (Join-Path $Runtime '_descargas')
        Move-Item (Join-Path $Runtime "_descargas\node-v$NodeVersion-win-x64") (Dir-Node)
    }
    Ok ("Node " + (& (Exe-Node) --version))

    Paso '2/8 PostgreSQL portable (se descarga desde npm, ~40 MB)'
    if (-not (Test-Path (Exe-Pg 'initdb'))) {
        $dl = Join-Path $Runtime '_descargas'
        Get-ChildItem $dl -Filter 'embedded-postgres-*.tgz' -ErrorAction SilentlyContinue | Remove-Item -Force
        Npm @('pack', $PgPackage, '--pack-destination', $dl, '--silent') $dl 'descargar PostgreSQL'
        $tgz = Get-ChildItem $dl -Filter 'embedded-postgres-*.tgz' | Select-Object -First 1
        if (-not $tgz) { Falla 'No se descargo PostgreSQL. Revise su conexion a internet.' }
        Extraer $tgz.FullName (Join-Path $Runtime 'pgsql')
        # El paquete puede traer enlaces simbolicos (Linux); en Windows la lista esta vacia.
        Ejecutar (Exe-Node) @('scripts/hydrate-symlinks.js') (Join-Path $Runtime 'pgsql/package') 'preparar PostgreSQL'
        if (-not $EsWindows) { Get-ChildItem (Join-Path (Dir-Pg) 'bin') | ForEach-Object { chmod +x $_.FullName } }
    }
    Ok 'PostgreSQL 16 listo'

    Paso '3/8 Configuracion y claves (se generan al azar, solo la primera vez)'
    if (-not (Test-Path $EnvFile)) {
        $pgPass = Texto-Aleatorio 16
        $jwt    = Texto-Aleatorio 32
        $lineas = @(
            "NODE_ENV=production", "HOST=127.0.0.1", "PORT=$PuertoApi",
            "DATABASE_URL=postgresql://anpe:$pgPass@127.0.0.1:$PuertoPg/postgres?schema=public",
            "PG_PASSWORD=$pgPass", "JWT_SECRET=$jwt",
            "STORAGE_DIR=$Storage", "PUBLIC_URL=http://localhost:$PuertoWeb", "FRONTEND_ORIGIN=http://localhost:$PuertoWeb",
            "COOKIE_SECURE=false", "LOGIN_RATE_LIMIT=30", "SWAGGER_ENABLED=false",
            "GAM_NOMBRE=Gobierno Autonomo Municipal de Prueba",
            "SEED_ADMIN_EMAIL=admin@gam.bo", "SEED_ADMIN_PASSWORD=AnpePrueba2026",
            "SEED_DEMO_USERS=true", "SEED_DEMO_PASSWORD=AnpePrueba2026"
        )
        Set-Content -Path $EnvFile -Value $lineas -Encoding ASCII
    }
    Cargar-Entorno
    # Durante la instalacion NO debe existir NODE_ENV=production: omitiria las herramientas de compilacion.
    $nodeEnvProduccion = $env:NODE_ENV
    Remove-Item Env:NODE_ENV -ErrorAction SilentlyContinue
    Ok 'Configuracion en windows\datos\anpe.env'

    Paso '4/8 Base de datos PostgreSQL'
    if (-not (Test-Path (Join-Path $PgData 'PG_VERSION'))) {
        $pw = Join-Path $Datos 'pw.tmp'
        Set-Content -Path $pw -Value $env:PG_PASSWORD -Encoding ASCII -NoNewline
        try { Ejecutar (Exe-Pg 'initdb') @('-D', $PgData, '-U', 'anpe', '-A', 'scram-sha-256', "--pwfile=$pw", '-E', 'UTF8', '--locale=C') $Proy 'crear la base de datos' }
        finally { Remove-Item $pw -Force -ErrorAction SilentlyContinue }
    }
    Pg-Iniciar
    Ok "PostgreSQL funcionando en 127.0.0.1:$PuertoPg"

    Paso '5/8 Programa servidor: descarga de librerias y compilacion (5 a 15 min)'
    if (-not (Test-Path (Join-Path $Backend 'node_modules/@nestjs/cli'))) { Npm @('ci', '--no-audit', '--no-fund') $Backend 'instalar librerias del servidor' }
    Npm @('run', 'build') $Backend 'compilar el servidor'
    Ok 'Servidor compilado'

    Paso '6/8 Programa de pantallas: descarga de librerias y compilacion (5 a 15 min)'
    if (-not (Test-Path (Join-Path $Frontend 'node_modules/tailwindcss'))) { Npm @('ci', '--no-audit', '--no-fund') $Frontend 'instalar librerias de las pantallas' }
    $env:BACKEND_URL = "http://127.0.0.1:$PuertoApi"
    Npm @('run', 'build') $Frontend 'compilar las pantallas'
    Ok 'Pantallas compiladas'

    Paso '7/8 Tablas de la base de datos y usuarios de prueba'
    $env:NODE_ENV = $nodeEnvProduccion
    Ejecutar (Exe-Node) @('node_modules/prisma/build/index.js', 'migrate', 'deploy') $Backend 'crear tablas'
    Ejecutar (Exe-Node) @('dist/seed.js') $Backend 'crear usuarios de prueba'
    Ok 'Base lista'

    Paso '8/8 Cerrando'
    Pg-Detener
    $exito = $true
    Write-Host ''
    Write-Host '=============================================================' -ForegroundColor Green
    Write-Host ' INSTALACION TERMINADA' -ForegroundColor Green
    Write-Host ' Siguiente paso: doble clic en 2-INICIAR.bat' -ForegroundColor Green
    Write-Host ' Usuarios (clave para todos: AnpePrueba2026):' -ForegroundColor Green
    Write-Host '   solicitante@gam.bo  presupuesto@gam.bo  contrataciones@gam.bo' -ForegroundColor Green
    Write-Host '   rpa@gam.bo          admin@gam.bo' -ForegroundColor Green
    Write-Host '=============================================================' -ForegroundColor Green
}
catch {
    Write-Host ''
    Write-Host '*************************************************************' -ForegroundColor Red
    Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ' Vuelva a ejecutar 1-INSTALAR.bat (retoma donde quedo).' -ForegroundColor Red
    Write-Host ' Si persiste, envie el archivo windows\datos\logs\instalacion.log' -ForegroundColor Red
    Write-Host '*************************************************************' -ForegroundColor Red
}
finally { Stop-Transcript | Out-Null }
if (-not $exito) { exit 1 }
