@echo off
title Sistema de Correspondencia - Detener
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalador\detener.ps1"
pause
