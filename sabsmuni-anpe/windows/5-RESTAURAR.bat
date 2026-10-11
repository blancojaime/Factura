@echo off
title SABSMUNI-ANPE - 5-RESTAURAR
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\restaurar.ps1"
echo.
pause
