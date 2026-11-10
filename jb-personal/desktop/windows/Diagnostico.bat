@echo off
REM Diagnostico: ejecuta JB-Personal en esta ventana para ver cualquier error en pantalla.
net session >nul 2>&1 || (powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs" & exit /b)
for %%I in ("%~dp0..\..") do set DIR=%%~fI
echo === Estado de la tarea ===
schtasks /Query /TN "JB-Personal" /FO LIST 2>&1 | findstr /I "Nombre TaskName Estado Status Ultimo Last"
echo.
echo === Ultimos fallos registrados ===
if exist "%ProgramData%\JB-Personal\logs\fallos.log" (powershell -NoProfile -Command "Get-Content '%ProgramData%\JB-Personal\logs\fallos.log' -Tail 25") else (echo (sin fallos.log))
echo.
echo === Ultimas lineas del registro del servicio ===
if exist "%ProgramData%\JB-Personal\logs\servicio.log" (powershell -NoProfile -Command "Get-Content '%ProgramData%\JB-Personal\logs\servicio.log' -Tail 15") else (echo (sin servicio.log))
echo.
echo === Probando el arranque en esta ventana (Ctrl+C para detener) ===
schtasks /End /TN "JB-Personal" >nul 2>&1
cd /d "%DIR%\desktop"
"%DIR%\python\python.exe" launcher.py --servicio
echo.
echo El proceso termino. Copie el texto de arriba y envielo a soporte.
pause
