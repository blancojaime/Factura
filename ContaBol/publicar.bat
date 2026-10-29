@echo off
REM Publica ContaBol como aplicacion autocontenida para Windows.
REM Uso: publicar.bat [x64|x86]   (debe coincidir con la edicion de Access Database Engine instalada)
set ARQ=%1
if "%ARQ%"=="" set ARQ=x64
dotnet publish ContaBol.App -c Release -r win-%ARQ% --self-contained true -p:PublishSingleFile=false -o publicar\win-%ARQ%
echo.
echo Listo: publicar\win-%ARQ%\ContaBol.App.exe
