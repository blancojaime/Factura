@echo off
REM Respaldo cifrado diario. Programar (cmd):
REM   schtasks /create /tn "GAM Respaldo" /tr "\"%LOCALAPPDATA%\Programs\GAMPersonal\desktop\respaldo_programado.bat\"" /sc daily /st 18:45
REM Defina GAM_BACKUP_PASSWORD como variable de entorno (no la escriba en este archivo).
if "%GAM_BACKUP_PASSWORD%"=="" (echo Falta la variable GAM_BACKUP_PASSWORD & exit /b 1)
if exist "%~dp0..\python\python.exe" (
  "%~dp0..\python\python.exe" "%~dp0launcher.py" --respaldo
) else (
  "%~dp0GAMPersonal.exe" --respaldo
)
exit /b %errorlevel%
