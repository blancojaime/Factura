@echo off
chcp 65001 >nul
title Crear instalador SIGAA Escritorio
cd /d "%~dp0"
echo ============================================
echo   Crear instalador de SIGAA para Windows
echo   (necesita internet; tarda 5 a 15 minutos)
echo ============================================
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js no esta instalado. Instale Node.js desde https://nodejs.org y vuelva a intentar.
  pause
  exit /b 1
)
echo.
echo [1/4] Preparando el sistema...
if not exist node_modules\.bin\vite.cmd (
  call npm install --include=dev --ignore-scripts
  if errorlevel 1 goto fallo
)
echo.
echo [2/4] Construyendo servidor y pantallas...
call npm run build
if errorlevel 1 goto fallo
echo.
echo [3/4] Preparando la aplicacion de escritorio...
cd desktop
call npm install --ignore-scripts
if errorlevel 1 goto fallo
echo.
echo [4/4] Creando el instalador...
call npm run dist
if errorlevel 1 goto sininstalador
echo.
echo ============================================
echo   LISTO. El instalador esta en la carpeta:
echo   %cd%\release
echo   Archivo: SIGAA Setup 1.0.0.exe
echo ============================================
start "" "%cd%\release"
pause
exit /b 0
:sininstalador
echo.
if exist "release\win-unpacked\SIGAA.exe" (
  echo ============================================
  echo   El instalador (.exe de instalacion) no se pudo crear,
  echo   pero el PROGRAMA SI QUEDO LISTO y funciona:
  echo   %cd%\release\win-unpacked\SIGAA.exe
  echo   Copie toda la carpeta win-unpacked a la PC donde lo usara.
  echo ============================================
  start "" "%cd%\release\win-unpacked"
  pause
  exit /b 0
)
:fallo
echo.
echo Fallo la creacion del instalador. Tome una foto de los mensajes en rojo y envieela.
pause
exit /b 1
