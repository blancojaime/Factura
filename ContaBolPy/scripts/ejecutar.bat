@echo off
REM Ejecuta ContaBol desde el codigo fuente (sin compilar).
cd /d "%~dp0\.."
if not exist .venv (python -m venv .venv && call .venv\Scripts\activate.bat && pip install -r requirements.txt) else call .venv\Scripts\activate.bat
python -m contabol
