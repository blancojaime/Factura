@echo off
title Sistema de Correspondencia - Iniciar para la red local
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalador\iniciar.ps1" -Red
pause
