@echo off
REM Menu para iniciar, detener o consultar el servicio JB-Personal (pide permisos de administrador)
net session >nul 2>&1 || (powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs" & exit /b)
:menu
cls
echo ============================================
echo   JB-Personal - Administrar el servicio
echo ============================================
schtasks /Query /TN "JB-Personal" /FO LIST 2>nul | findstr /B "Estado Status"
echo.
echo   1. Iniciar        2. Detener        3. Reiniciar
echo   4. Abrir en el navegador            5. Ver registro (log)
echo   6. Abrir carpeta de datos y respaldos         0. Salir
set /p op=Opcion: 
if "%op%"=="1" schtasks /Run /TN "JB-Personal"
if "%op%"=="2" (schtasks /End /TN "JB-Personal" & powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0detener_servicio.ps1" -Dir "%~dp0..\..")
if "%op%"=="3" (powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0detener_servicio.ps1" -Dir "%~dp0..\.." & schtasks /Run /TN "JB-Personal")
if "%op%"=="4" start "" "%~dp0..\..\python\python.exe" "%~dp0..\launcher.py"
if "%op%"=="5" notepad "%ProgramData%\JB-Personal\logs\servicio.log"
if "%op%"=="6" explorer "%ProgramData%\JB-Personal"
if "%op%"=="0" exit /b
timeout /t 3 >nul
goto menu
