@echo off
chcp 65001 >nul
title SICOM-MUNI - Iniciar
cd /d "%~dp0"
echo ============================================================
echo   SICOM-MUNI - Inicio automatico
echo ============================================================
echo.
docker --version >nul 2>&1
if errorlevel 1 (
  echo [X] Docker Desktop no esta instalado.
  echo     Instalelo desde https://www.docker.com/products/docker-desktop y vuelva a ejecutar este archivo.
  pause
  exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
  echo [X] Docker Desktop esta instalado pero NO esta abierto.
  echo     Abralo desde el menu Inicio, espere a que el icono de la ballena quede quieto y vuelva a ejecutar este archivo.
  pause
  exit /b 1
)
echo [1/4] Preparando claves de seguridad...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0preparar_env.ps1"
if errorlevel 1 ( echo [X] No se pudo crear el archivo .env & pause & exit /b 1 )
echo.
echo [2/4] Construyendo e iniciando el sistema (la primera vez tarda entre 5 y 15 minutos)...
docker compose up -d --build
if errorlevel 1 ( echo [X] Fallo al iniciar. Copie el mensaje de arriba y envielo a soporte. & pause & exit /b 1 )
echo.
echo [3/4] Cargando usuarios y datos de demostracion...
docker compose --profile seed run --rm seed
if errorlevel 1 ( echo [X] Fallo la carga de datos demo. & pause & exit /b 1 )
echo.
echo [4/4] Abriendo el sistema en el navegador...
timeout /t 8 /nobreak >nul
start "" http://localhost:3000
echo.
echo ============================================================
echo   LISTO. Si el navegador no se abrio, entre a: http://localhost:3000
echo   Usuario: solicitante     Clave: Sicom#2026Demo
echo   (otros usuarios: presupuesto, contrataciones, rpa, recepcion, admin)
echo   Para apagar el sistema ejecute DETENER-WINDOWS.bat
echo ============================================================
pause
