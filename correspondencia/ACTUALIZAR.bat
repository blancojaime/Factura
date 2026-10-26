@echo off
title Sistema de Correspondencia - Actualizar a una version nueva
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalador\actualizar.ps1"
pause
