. "$PSScriptRoot\comun.ps1"
try { Escribir 'Deteniendo el sistema...' 'Cyan'; Detener-Todo; Ok 'Sistema detenido. Ya puede apagar la computadora con tranquilidad.' } catch { Fallo $_.Exception.Message; exit 1 }
