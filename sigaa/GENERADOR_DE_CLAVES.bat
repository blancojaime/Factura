@echo off
chcp 65001 >nul
title SIGAA - Generador de claves de activacion
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 ( echo No se encontro Node.js. Instalelo desde https://nodejs.org & pause & exit /b 1 )
node tools\licencias\generador.mjs
pause
