@echo off
REM Instalador SIC-MUNI: doble clic. Ejecuta Instalar-SICMUNI.ps1 sin cambiar la politica de ejecucion del sistema.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar-SICMUNI.ps1" %*
echo.
pause
