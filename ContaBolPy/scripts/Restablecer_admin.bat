@echo off
chcp 65001 >nul
title CONTA JB - Restablecer administrador
rem Busca CONTA JB (instalado o portable) y abre el restablecimiento del usuario admin.
set "EXE="
if exist "%~dp0ContaJB.exe" set "EXE=%~dp0ContaJB.exe"
if not defined EXE if exist "%LOCALAPPDATA%\Programs\ContaJB\ContaJB.exe" set "EXE=%LOCALAPPDATA%\Programs\ContaJB\ContaJB.exe"
if not defined EXE if exist "%ProgramFiles%\ContaJB\ContaJB.exe" set "EXE=%ProgramFiles%\ContaJB\ContaJB.exe"
if not defined EXE if exist "%~dp0ContaJB\ContaJB.exe" set "EXE=%~dp0ContaJB\ContaJB.exe"
if not defined EXE (
  echo No se encontro ContaJB.exe. Copie este archivo dentro de la carpeta de CONTA JB y vuelva a ejecutarlo.
  pause
  exit /b 1
)
start "" "%EXE%" --restablecer-admin
