@echo off
rem ==========================================================
rem  Instalador del Sistema de Correspondencia (una sola maquina)
rem  Haga doble clic. No necesita permisos de administrador.
rem ==========================================================
title Instalador - Sistema de Correspondencia
chcp 65001 >nul
cd /d "%~dp0"
if not exist "instalador\instalar.ps1" (
  echo No se encuentra instalador\instalar.ps1
  echo Asegurese de haber EXTRAIDO todo el ZIP antes de ejecutar este archivo.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalador\instalar.ps1"
if errorlevel 1 (
  echo.
  echo *** La instalacion NO termino correctamente. Lea el mensaje de arriba.
  echo *** Detalles en: instalador\instalacion.log
)
pause
