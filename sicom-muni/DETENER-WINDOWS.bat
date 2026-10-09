@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Apagando SICOM-MUNI (sus datos se conservan)...
docker compose down
echo Listo. Para volver a encender use INICIAR-WINDOWS.bat
pause
