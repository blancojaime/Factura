. "$PSScriptRoot\comun.ps1"
Preparar-Path
Paso 'Apagando servidor y pantallas'
Detener-Aplicacion; Ok 'Apagados'
Paso 'Apagando la base de datos (guarda todo de forma segura)'
if (Test-Path (Exe-Pg 'pg_ctl')) { Pg-Detener }
Ok 'Sistema apagado. Sus datos quedan guardados en windows\datos'
