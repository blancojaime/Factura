@echo off
title SABSMUNI-ANPE - 3-DETENER
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\detener.ps1"
echo.
pause
