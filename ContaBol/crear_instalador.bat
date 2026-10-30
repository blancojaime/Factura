@echo off
REM Crea ContaBol_Setup_<arq>.exe. Requiere SDK .NET 8 e Inno Setup 6 (https://jrsoftware.org/isdl.php).
REM Uso: crear_instalador.bat [x64|x86]
cd /d "%~dp0"
set ARQ=%1
if "%ARQ%"=="" set ARQ=x64
call publicar.bat %ARQ% nopause
if errorlevel 1 exit /b 1
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo No se encontro Inno Setup 6. Instalelo desde https://jrsoftware.org/isdl.php
  pause
  exit /b 1
)
%ISCC% /DArq=%ARQ% /DOrigen=..\publicar\win-%ARQ% instalador\ContaBol.iss
echo.
echo Instalador: instalador\salida\ContaBol_Setup_%ARQ%.exe
pause
