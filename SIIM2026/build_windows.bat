@echo off
REM Compilación del instalador de SIIM 2026 (ejecutar en Windows 10/11 con Python 3.11+ e Inno Setup 6 instalados)
setlocal
cd /d %~dp0
if not exist siim\resources\license_pub.pem (
  echo [AVISO] Falta siim\resources\license_pub.pem: ejecute primero "python tools\licencias.py init" para crear su clave de licencias.
  echo         Sin ella el instalador sólo funcionará en periodo de prueba.
  pause
)
python -m pip install -r requirements-dev.txt || exit /b 1
set QT_QPA_PLATFORM=offscreen
python -m pytest -q tests || exit /b 1
set QT_QPA_PLATFORM=
pyinstaller --noconfirm --clean siim2026.spec || exit /b 1
echo Autoprueba del ejecutable...
dist\SIIM2026\SIIM2026.exe --selftest || exit /b 1
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer\siim2026.iss || exit /b 1
echo.
echo Listo: dist\SIIM2026_Setup_1.0.0.exe
