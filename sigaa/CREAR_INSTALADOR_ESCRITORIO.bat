@echo off
chcp 65001 >nul
title Crear instalador SIGAA Escritorio
cd /d "%~dp0"
set REPARADO=0
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
:construir
echo.
echo [2/4] Construyendo servidor y pantallas...
call npm run build
if errorlevel 1 goto reparar
echo.
echo [3/4] Preparando la aplicacion de escritorio...
cd desktop
call npm install --ignore-scripts
if errorlevel 1 goto reparar_desktop
echo.
echo [4/4] Creando el instalador...
if exist release rmdir /s /q release
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

:reparar
cd /d "%~dp0"
if "%REPARADO%"=="1" goto fallo
set REPARADO=1
echo.
echo ============================================
echo   Un componente se instalo incompleto o danado
echo   (por ejemplo: "no es una aplicacion Win32 valida").
echo   Se repara solo: se borra la carpeta node_modules
echo   y se vuelve a instalar. Espere unos minutos...
echo ============================================
if exist node_modules rmdir /s /q node_modules
if exist node_modules (
  echo No se pudo borrar la carpeta node_modules. Cierre otros programas que la usen ^(antivirus, explorador^) y vuelva a intentar.
  goto fallo
)
call npm cache verify
call npm install --include=dev --ignore-scripts
if errorlevel 1 goto fallo
goto construir

:reparar_desktop
cd /d "%~dp0"
if "%REPARADO%"=="1" goto fallo
set REPARADO=1
echo.
echo   La instalacion de la aplicacion de escritorio fallo. Se repara y se reintenta...
if exist desktop\node_modules rmdir /s /q desktop\node_modules
call npm cache verify
cd desktop
call npm install --ignore-scripts
if errorlevel 1 goto fallo
echo.
echo [4/4] Creando el instalador...
if exist release rmdir /s /q release
call npm run dist
if errorlevel 1 goto sininstalador
echo.
echo   LISTO. El instalador esta en: %cd%\release
start "" "%cd%\release"
pause
exit /b 0

:sininstalador
echo.
if exist "release\win-unpacked\SIGAA.exe" (
  echo ============================================
  echo   El instalador ^(.exe de instalacion^) no se pudo crear,
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
