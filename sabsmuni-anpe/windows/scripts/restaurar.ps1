# Restaura un respaldo (reemplaza TODOS los datos actuales).
. "$PSScriptRoot\comun.ps1"
try {
    $dest = Join-Path $Datos 'respaldos'
    $lista = @(Get-ChildItem $dest -Filter 'anpe-*.zip' -ErrorAction SilentlyContinue | Sort-Object Name -Descending)
    if (-not $lista.Count) { Falla 'No hay respaldos en windows\datos\respaldos. Copie ahi el archivo .zip y repita.' }
    Write-Host 'Respaldos disponibles:'
    for ($i = 0; $i -lt $lista.Count; $i++) { Write-Host ("  [{0}] {1}" -f ($i + 1), $lista[$i].Name) }
    $n = [int](Read-Host 'Numero del respaldo a restaurar')
    if ($n -lt 1 -or $n -gt $lista.Count) { Falla 'Numero invalido.' }
    $conf = Read-Host 'Esto REEMPLAZA los datos actuales. Escriba SI para continuar'
    if ($conf -ne 'SI') { Falla 'Cancelado.' }
    Preparar-Path
    Detener-Aplicacion; Pg-Detener
    foreach ($d in @($PgData, $Storage)) { if (Test-Path $d) { Remove-Item $d -Recurse -Force } }
    $tmp = Join-Path $Datos '_restaurar'
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Expand-Archive -Path $lista[$n - 1].FullName -DestinationPath $tmp -Force
    Move-Item (Join-Path $tmp 'pgdata') $PgData
    Move-Item (Join-Path $tmp 'storage') $Storage
    Move-Item (Join-Path $tmp 'anpe.env') $EnvFile -Force
    Remove-Item $tmp -Recurse -Force
    if (-not $EsWindows) { chmod 700 $PgData }   # PostgreSQL en Linux exige 0700
    Ok 'Respaldo restaurado. Ahora ejecute 2-INICIAR.bat'
}
catch { Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red; exit 1 }
