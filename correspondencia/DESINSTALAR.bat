@echo off
title Sistema de Correspondencia - Desinstalar
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalador\desinstalar.ps1"
pause
