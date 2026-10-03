@echo off
chcp 65001 >nul
title SIGAA - Sistema de Almacenes, Combustible y Activos Fijos
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo No se encontro Node.js. Instalelo desde https://nodejs.org y vuelva a abrir este archivo.
  pause
  exit /b 1
)

if not exist node_modules\.bin\vite.cmd (
  echo [1/3] Instalando componentes. Puede tardar varios minutos, espere...
  call npm install --include=dev
  if errorlevel 1 ( echo Fallo la instalacion. Revise su conexion a internet. & pause & exit /b 1 )
)

if not exist web\dist\index.html (
  echo [2/3] Preparando el sistema...
  call npm run build
  if errorlevel 1 ( echo Fallo la preparacion. & pause & exit /b 1 )
)

if not exist server\data\sigaa.sqlite (
  echo [3/3] Creando la base de datos con datos de ejemplo...
  call npm run seed
  if errorlevel 1 ( echo Fallo la creacion de la base de datos. & pause & exit /b 1 )
)

echo.
echo ============================================================
echo  SIGAA se esta iniciando. Se abrira su navegador en unos segundos.
echo  NO CIERRE ESTA VENTANA mientras use el sistema.
echo  Direccion: http://localhost:3000   Usuario: admin   Clave: Admin2026
echo ============================================================
start "" cmd /c "timeout /t 8 >nul & start http://localhost:3000"
call npm start
pause
