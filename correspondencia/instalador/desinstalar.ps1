. "$PSScriptRoot\comun.ps1"
Escribir 'DESINSTALAR: se borrarán la base de datos, los programas descargados y los archivos adjuntos de esta instalación.' 'Yellow'
Escribir 'Los respaldos de la carpeta "respaldos" NO se borran.' 'Yellow'
$r = Read-Host 'Escriba SI (en mayúsculas) para continuar'
if ($r -cne 'SI') { Escribir 'Cancelado. No se borró nada.'; exit 0 }
try {
    try { Detener-Todo } catch {}
    Get-ChildItem $Runtime -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $Raiz 'config\config.php'), (Join-Path $Raiz 'storage\installed.lock'), (Join-Path $Raiz 'CLAVES_TEMPORALES.csv') -Force -ErrorAction SilentlyContinue
    Get-ChildItem (Join-Path $Raiz 'storage\uploads') -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' } | Remove-Item -Force
    Remove-Item (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Correspondencia.lnk') -Force -ErrorAction SilentlyContinue
    Ok 'Desinstalado. Puede borrar la carpeta completa si ya no la necesita, o ejecutar INSTALAR.bat para empezar de cero.'
} catch { Fallo $_.Exception.Message; exit 1 }
