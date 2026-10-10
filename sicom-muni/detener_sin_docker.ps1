# Apaga SICOM-MUNI (modo sin Docker). Los datos se conservan en la carpeta .local
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root '.local\pids.txt'
if (Test-Path $pidFile) {
    foreach ($p in Get-Content $pidFile) { try { Stop-Process -Id ([int]$p) -Force -ErrorAction Stop } catch { } }
    Remove-Item $pidFile -Force
}
foreach ($port in 3000, 8000) {
    try {
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    } catch { }
}
Write-Host 'SICOM-MUNI apagado. Para volver a encenderlo use INICIAR-SIN-DOCKER.bat'
Read-Host 'Presione Enter para cerrar'
