@echo off
REM  Deja el acceso solo en esta PC (cierra el puerto en el Firewall)
net session >nul 2>&1 || (powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs" & exit /b)
for %%I in ("%~dp0..\..") do set DIR=%%~fI
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_servicio.ps1" -Dir "%DIR%" 
echo.
echo Listo. Si habilito el acceso de red, use http://IP-DE-ESTA-PC:8765/ desde las otras PC.
pause
