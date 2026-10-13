. "$PSScriptRoot\comun.ps1"
try {
    if (-not (Test-Path $Puertos)) { Fallo 'El sistema no está instalado.'; exit 1 }
    Db-Iniciar
    $cfg = Leer-Json $Puertos; $s = Leer-Json $Secretos
    $dir = Join-Path $Raiz 'respaldos'; New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $sello = Get-Date -Format 'yyyyMMdd_HHmmss'
    $sql = Join-Path $dir "base_$sello.sql"
    $env:MYSQL_PWD = $s.app
    & (Db-Dump) '-ucorr' '-h127.0.0.1' "-P$($cfg.db)" '--single-transaction' '--default-character-set=utf8mb4' "--result-file=$sql" 'correspondencia'
    Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) { throw 'Falló la copia de la base de datos.' }
    $up = Join-Path $Raiz 'storage\uploads'
    $archivos = Get-ChildItem $up -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' }
    if ($archivos) { Compress-Archive -Path ($archivos.FullName) -DestinationPath (Join-Path $dir "archivos_$sello.zip") -Force }
    Ok "Respaldo creado en la carpeta: $dir"
    Escribir "  Copie esa carpeta a un pendrive o disco externo para mayor seguridad." 'Yellow'
    exit 0
} catch { Fallo $_.Exception.Message; exit 1 }
