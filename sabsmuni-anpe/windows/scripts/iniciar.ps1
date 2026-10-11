# Enciende PostgreSQL, el servidor y las pantallas, y abre el navegador.
. "$PSScriptRoot\comun.ps1"
try {
    if (-not (Test-Path $EnvFile)) { Falla 'El sistema no esta instalado. Ejecute primero 1-INSTALAR.bat' }
    Preparar-Path; Cargar-Entorno
    New-Item -ItemType Directory -Force -Path $Logs | Out-Null

    Paso 'Encendiendo la base de datos'
    Pg-Iniciar; Ok 'Base de datos encendida'

    Paso 'Aplicando actualizaciones de la base (si las hay)'
    Ejecutar (Exe-Node) @('node_modules/prisma/build/index.js', 'migrate', 'deploy') $Backend 'actualizar tablas'

    Paso 'Encendiendo el servidor y las pantallas'
    Detener-Aplicacion
    $extra = @{}; if ($EsWindows) { $extra['WindowStyle'] = 'Hidden' }
    $be = Start-Process -FilePath (Exe-Node) -ArgumentList 'dist/main.js' -WorkingDirectory $Backend -PassThru `
          -RedirectStandardOutput (Join-Path $Logs 'servidor.log') -RedirectStandardError (Join-Path $Logs 'servidor-errores.log') @extra
    $fe = Start-Process -FilePath (Exe-Node) -ArgumentList @('node_modules/next/dist/bin/next', 'start', '-p', "$PuertoWeb", '-H', '127.0.0.1') -WorkingDirectory $Frontend -PassThru `
          -RedirectStandardOutput (Join-Path $Logs 'pantallas.log') -RedirectStandardError (Join-Path $Logs 'pantallas-errores.log') @extra
    @{ backend = $be.Id; frontend = $fe.Id } | ConvertTo-Json | Set-Content $PidFile

    Write-Host '    Esperando que el sistema responda (hasta 2 minutos)...'
    $apiOk = Esperar-Url "http://127.0.0.1:$PuertoApi/api/health" 120
    $webOk = Esperar-Url "http://127.0.0.1:$PuertoWeb/login" 120
    if (-not ($apiOk -and $webOk)) { Falla 'El sistema no respondio. Revise windows\datos\logs\servidor-errores.log y pantallas-errores.log' }

    Write-Host ''
    Write-Host '=============================================================' -ForegroundColor Green
    Write-Host " SISTEMA ENCENDIDO:  http://localhost:$PuertoWeb" -ForegroundColor Green
    Write-Host ' Clave de todos los usuarios: AnpePrueba2026' -ForegroundColor Green
    Write-Host ' Para apagarlo: 3-DETENER.bat  (puede cerrar esta ventana)' -ForegroundColor Green
    Write-Host '=============================================================' -ForegroundColor Green
    if ($EsWindows) { Start-Process "http://localhost:$PuertoWeb" }
}
catch {
    Write-Host ''
    Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
