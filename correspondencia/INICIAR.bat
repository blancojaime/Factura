@echo off
title Sistema de Correspondencia - Iniciar
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalador\iniciar.ps1"
if errorlevel 1 pause
