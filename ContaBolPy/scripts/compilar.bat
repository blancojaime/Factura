@echo off
REM Genera ContaBol.exe (PyInstaller) y el instalador (Inno Setup). Requiere Python 3.10+ en el PATH.
REM Uso: scripts\compilar.bat
cd /d "%~dp0\.."
where python >nul 2>nul || (echo Instale Python 3.10 o superior desde https://www.python.org/downloads/ & pause & exit /b 1)
python -m venv .venv || goto error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip || goto error
pip install -r requirements-dev.txt || goto error
python -m pytest -q || goto error
pyinstaller contabol.spec --noconfirm || goto error
echo.
echo Ejecutable: dist\ContaBol\ContaBol.exe
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
  %ISCC% scripts\instalador.iss && echo Instalador: dist\ContaBol_Setup_2.0.0.exe
) else (
  echo Para crear el instalador instale Inno Setup 6: https://jrsoftware.org/isdl.php
)
pause
exit /b 0
:error
echo Ocurrio un error. Revise los mensajes anteriores.
pause
exit /b 1
