@echo off
REM ============================================================
REM  Compila GAMPersonal para Windows 10+ (ejecutar en Windows)
REM  Requisitos: Python 3.11+ (64 bits) en PATH.  Opcional: NSIS (makensis) para el instalador.
REM ============================================================
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip || goto :error
pip install -r requirements-desktop.txt || goto :error
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller gam_personal.spec --noconfirm || goto :error
echo.
echo [OK] Ejecutable en: %cd%\dist\GAMPersonal\GAMPersonal.exe
where makensis >nul 2>nul
if %errorlevel%==0 (
  makensis installer.nsi || goto :error
  echo [OK] Instalador: %cd%\GAMPersonal_Setup.exe
) else (
  echo [AVISO] NSIS no instalado: se omite el instalador. Puede distribuir la carpeta dist\GAMPersonal.
)
exit /b 0
:error
echo [ERROR] La compilacion fallo. Revise los mensajes anteriores.
exit /b 1
