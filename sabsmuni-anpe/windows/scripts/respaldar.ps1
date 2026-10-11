# Respaldo "en frio": apaga el sistema, comprime base + documentos y lo vuelve a encender si estaba encendido.
. "$PSScriptRoot\comun.ps1"
try {
    if (-not (Test-Path $PgData)) { Falla 'No hay datos que respaldar (aun no se instalo).' }
    Preparar-Path
    $estabaEncendido = (Test-Path $PidFile) -or (Pg-Corriendo)
    Paso 'Apagando el sistema para un respaldo consistente'
    Detener-Aplicacion; Pg-Detener
    $dest = Join-Path $Datos 'respaldos'
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $zip = Join-Path $dest ("anpe-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + ".zip")
    Paso 'Comprimiendo base de datos y documentos (puede tardar)'
    Compress-Archive -Path $PgData, $Storage, $EnvFile -DestinationPath $zip -CompressionLevel Optimal
    $hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
    Set-Content -Path "$zip.sha256" -Value "$hash  $(Split-Path -Leaf $zip)"
    Ok "Respaldo: $zip"
    Ok "SHA-256: $hash"
    Write-Host '    Copie ese archivo a un pendrive o a otra computadora.' -ForegroundColor Yellow
    if ($estabaEncendido) { Paso 'Volviendo a encender'; & "$PSScriptRoot\iniciar.ps1" }
}
catch { Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red; exit 1 }
