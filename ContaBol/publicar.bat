@echo off
REM Publica ContaBol como aplicacion autocontenida. Requiere el SDK de .NET 8.
REM Uso: publicar.bat [x64|x86]
cd /d "%~dp0"
set ARQ=%1
if "%ARQ%"=="" set ARQ=x64
where dotnet >nul 2>nul
if errorlevel 1 (
  echo No se encontro .NET SDK 8. Descarguelo de https://dotnet.microsoft.com/download/dotnet/8.0
  echo O use el ejecutable ya compilado: carpeta dist\ContaBol_%ARQ%.zip
  pause
  exit /b 1
)
dotnet publish ContaBol.App -c Release -r win-%ARQ% --self-contained true -o publicar\win-%ARQ%
if errorlevel 1 (
  echo Error al publicar.
  pause
  exit /b 1
)
echo.
echo Listo: publicar\win-%ARQ%\ContaBol.exe
pause
