@echo off
REM ============================================================================
REM  Compila el Importador Excel -> VSIAF en Windows.
REM  Requisitos: Python 3.12 (64 bits, con "tcl/tk" - viene por defecto) e Inno Setup 6.
REM  Uso:  doble clic, o desde cmd:  packaging\build_windows.bat
REM ============================================================================
setlocal
cd /d "%~dp0\.."

if not exist .venv (
  py -3.12 -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip || goto :error
python -m pip install -r requirements-dev.txt || goto :error

echo.
echo === Pruebas ===
python -m pytest -q tests || goto :error

echo.
echo === Ejecutable (PyInstaller) ===
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
pyinstaller packaging\ImportadorVSIAF.spec --noconfirm || goto :error

echo.
echo === Documentos ===
mkdir dist\docs
python -m vsiaf_importer plantilla dist\docs\plantilla_importacion_vsiaf.xlsx || goto :error
python -m vsiaf_importer plantilla dist\docs\plantilla_con_ejemplos.xlsx --ejemplos || goto :error
copy GUIA_DE_USO.md dist\docs\ >nul
if exist GUIA_DE_USO.docx copy GUIA_DE_USO.docx dist\docs\ >nul

echo.
echo === Instalador (Inno Setup) ===
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
  %ISCC% packaging\instalador.iss || goto :error
  echo Instalador: dist\Setup_ImportadorVSIAF_1.0.0.exe
) else (
  echo [AVISO] Inno Setup 6 no esta instalado: se omite el instalador. La carpeta dist\ImportadorVSIAF es portable.
)
echo.
echo LISTO.
exit /b 0

:error
echo.
echo *** ERROR en la compilacion ***
exit /b 1
