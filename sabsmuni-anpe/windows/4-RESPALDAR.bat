@echo off
title SABSMUNI-ANPE - 4-RESPALDAR
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\respaldar.ps1"
echo.
pause
