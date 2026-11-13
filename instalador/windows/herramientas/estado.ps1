# Muestra el estado de SICOM-MUNI: servicios, direcciones, licencia y último respaldo.
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
$e = Leer-Env
$puerto = $e['SERVIDOR_PUERTO']
Write-Host "=== SICOM-MUNI: estado ===`n"
foreach ($s in $SvcBd, $SvcApp) {
    $x = Get-Service -Name $s -ErrorAction SilentlyContinue
    Write-Host ("  Servicio {0,-14} : {1}" -f $s, $(if ($x) { $x.Status } else { 'NO INSTALADO' }))
}
$salud = $false
try { $salud = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$puerto/api/v1/salud" -TimeoutSec 5).StatusCode -eq 200 } catch { }
Write-Host ("  Respuesta del sistema   : {0}" -f $(if ($salud) { 'CORRECTA' } else { 'SIN RESPUESTA' }))
Write-Host "`n  Dirección para la red   : $($e['PUBLIC_BASE_URL'])/"
Write-Host "  En este equipo          : http://localhost:$puerto/"
try {
    $l = Invoke-RestMethod -Uri "http://127.0.0.1:$puerto/api/v1/licencia" -UseBasicParsing
    Write-Host "`n  ID del equipo           : $($l.id_equipo)"
    Write-Host "  Licencia                : $($l.mensaje)"
} catch { }
$ult = Get-ChildItem (Join-Path $DataDir 'respaldos') -Filter 'sicom_*.dump' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host ("`n  Último respaldo         : {0}" -f $(if ($ult) { '{0:dd/MM/yyyy HH:mm}  ({1})' -f $ult.LastWriteTime, $ult.Name } else { 'ninguno todavía' }))
Write-Host "  Carpeta de datos        : $DataDir`n"
Read-Host 'Presione Enter para cerrar'
