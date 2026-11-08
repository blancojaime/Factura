@echo off
REM Respaldo cifrado diario con el programa instalado. Programar (cmd como administrador):
REM   schtasks /create /tn "GAM Respaldo" /tr "\"C:\Program Files\GAMPersonal\respaldo_programado.bat\"" /sc daily /st 18:45
REM Defina GAM_BACKUP_PASSWORD como variable de entorno del SISTEMA (no la escriba en este archivo).
if "%GAM_BACKUP_PASSWORD%"=="" (echo Falta la variable GAM_BACKUP_PASSWORD & exit /b 1)
"%~dp0GAMPersonal.exe" --respaldo
exit /b %errorlevel%
