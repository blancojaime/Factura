@echo off
title SABSMUNI-ANPE - 1-INSTALAR
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\instalar.ps1"
echo.
pause
