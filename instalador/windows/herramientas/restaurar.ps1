# Restaura un respaldo de SICOM-MUNI (reemplaza los datos actuales).
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
Exigir-Administrador $MyInvocation.MyCommand.Path
$LogFile = 'restauracion.log'
try {
    $dest = Join-Path $DataDir 'respaldos'
    $lista = @(Get-ChildItem $dest -Filter 'sicom_*.dump' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    if ($lista.Count -eq 0) { Write-Host 'No hay respaldos en' $dest; Read-Host 'Enter para cerrar'; exit 0 }
    Write-Host "Respaldos disponibles:`n"
    for ($i = 0; $i -lt $lista.Count; $i++) { Write-Host ("  [{0}] {1}   ({2:dd/MM/yyyy HH:mm})" -f ($i + 1), $lista[$i].Name, $lista[$i].LastWriteTime) }
    $n = Read-Host "`nEscriba el número del respaldo a restaurar (o Enter para cancelar)"
    if (-not $n) { exit 0 }
    $idx = [int]$n - 1
    if ($idx -lt 0 -or $idx -ge $lista.Count) { throw 'Número inválido' }
    $dump = $lista[$idx].FullName
    $conf = Read-Host "ATENCIÓN: se reemplazarán TODOS los datos actuales por los de $($lista[$idx].Name). Escriba SI para continuar"
    if ($conf -ne 'SI') { Write-Host 'Cancelado.'; exit 0 }
    $bd = Datos-Bd
    Stop-Service -Name $SvcApp -Force -ErrorAction SilentlyContinue
    $env:PGPASSWORD = $bd.Clave
    $x = Invocar-Nativo (Join-Path $InstallDir 'pgsql\bin\pg_restore.exe') @('-h', $bd.Host, '-p', $bd.Puerto, '-U', $bd.Usuario, '-d', $bd.Base, '--clean', '--if-exists', '--no-owner', $dump)
    $codigo = $x.Codigo
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    $zip = $dump -replace 'sicom_', 'archivos_' -replace '\.dump$', '.zip'
    if (Test-Path $zip) {
        $origen = Join-Path $DataDir 'archivos'
        Get-ChildItem $origen -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
        Expand-Archive -Path $zip -DestinationPath $origen -Force
    }
    Start-Service -Name $SvcApp
    Escribir-Log "Restauración de $dump (pg_restore código $codigo)" $LogFile
    Write-Host "`nRestauración terminada (código $codigo; 0 = sin errores; un código 1 con avisos suele ser normal)."
    Read-Host 'Presione Enter para cerrar'
}
catch { Escribir-Log ("ERROR: " + $_.Exception.Message) $LogFile; Read-Host 'Hubo un error. Presione Enter para cerrar'; exit 1 }
