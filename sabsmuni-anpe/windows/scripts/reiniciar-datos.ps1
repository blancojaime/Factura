# Borra TODOS los datos de prueba (procesos, usuarios creados, documentos) y deja el sistema como recien instalado.
. "$PSScriptRoot\comun.ps1"
$conf = Read-Host 'Esto BORRA todos los procesos y documentos de prueba. Escriba SI para continuar'
if ($conf -ne 'SI') { Write-Host 'Cancelado.'; exit 0 }
Preparar-Path
Detener-Aplicacion; Pg-Detener
foreach ($d in @($PgData, $Storage)) { if (Test-Path $d) { Remove-Item $d -Recurse -Force } }
if (Test-Path $EnvFile) { Remove-Item $EnvFile -Force }
& "$PSScriptRoot\instalar.ps1"
