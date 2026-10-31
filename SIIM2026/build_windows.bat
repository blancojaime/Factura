@echo off
chcp 65001 >nul
REM ===== Compilación de SIIM 2026 en Windows. Doble clic. Requiere Python 3.11+ (marque "Add Python to PATH" al instalarlo) =====
setlocal
cd /d %~dp0
where python >nul 2>nul || (echo [ERROR] No se encontro Python. Instale Python 3.12 desde python.org y marque "Add Python to PATH". & pause & exit /b 1)
python -m pip install -r requirements-dev.txt || (pause & exit /b 1)
set QT_QPA_PLATFORM=offscreen
python -m pytest -q tests || (echo [ERROR] Fallaron las pruebas. & pause & exit /b 1)
set QT_QPA_PLATFORM=
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm --clean siim2026.spec || (pause & exit /b 1)
dist\SIIM2026\SIIM2026.exe --selftest || (echo [ERROR] La autoprueba fallo. & pause & exit /b 1)
powershell -NoProfile -Command "Compress-Archive -Path dist\SIIM2026\* -DestinationPath dist\SIIM2026_Portable.zip -Force"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" ( "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer\siim2026.iss ) else ( echo [AVISO] Inno Setup 6 no esta instalado: se omite el instalador. Use SIIM2026_Portable.zip o instale Inno Setup desde jrsoftware.org )
rmdir /s /q build
echo.
echo ================================================================
echo  LISTO. Los archivos finales estan en la carpeta  dist\
echo    dist\SIIM2026_Setup_1.0.0.exe   (instalador de un clic)
echo    dist\SIIM2026_Portable.zip      (sin instalar: descomprimir y ejecutar SIIM2026.exe)
echo  NO ejecute nada de la carpeta "build": son archivos temporales.
echo ================================================================
start "" dist
pause
