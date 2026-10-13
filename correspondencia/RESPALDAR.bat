@echo off
title Sistema de Correspondencia - Respaldo
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalador\respaldar.ps1"
pause
