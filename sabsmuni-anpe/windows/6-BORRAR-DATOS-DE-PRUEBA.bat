@echo off
title SABSMUNI-ANPE - 6-BORRAR-DATOS-DE-PRUEBA
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\reiniciar-datos.ps1"
echo.
pause
