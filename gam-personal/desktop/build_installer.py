#!/usr/bin/env python3
"""Construye GAMPersonal_Setup.exe (instalador sencillo, autónomo) para Windows 10+ de 64 bits.

Funciona desde Linux, macOS o Windows. No usa PyInstaller: empaqueta Python embebido oficial + librerías
(wheels win_amd64) + el código, y lo envuelve con NSIS.
Requisitos en la máquina que construye: Python 3.9+, acceso a Internet (pypi.org y python.org) y NSIS (`makensis`).
Uso:  python build_installer.py [--version 1.0.0] [--manual ruta/Manual.pdf ...]
"""
import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

PYVER = "3.12.8"
AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
BUILD = AQUI / "build_setup"
STAGE = BUILD / "stage"
REQS = ["fastapi", "uvicorn", "sqlalchemy>=2.0", "python-multipart", "pyjwt", "openpyxl", "python-docx", "reportlab", "cryptography"]


def bajar(url: str, destino: Path):
    if destino.exists():
        return
    print("Descargando", url)
    destino.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, destino)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--manual", nargs="*", default=[], help="archivos de manual a incluir (PDF/DOCX)")
    a = ap.parse_args()
    if not shutil.which("makensis"):
        sys.exit("Falta NSIS (makensis). Linux: apt install nsis · Windows: https://nsis.sourceforge.io")
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    # 1) Python embebido
    zip_py = BUILD / f"python-{PYVER}-embed-amd64.zip"
    bajar(f"https://www.python.org/ftp/python/{PYVER}/python-{PYVER}-embed-amd64.zip", zip_py)
    with zipfile.ZipFile(zip_py) as z:
        z.extractall(STAGE / "python")
    pth = next((STAGE / "python").glob("python*._pth"))
    pth.write_text("python312.zip\n.\n..\\backend\n..\\site-packages\nimport site\n", encoding="utf-8")

    # 2) Librerías (solo wheels binarios para Windows)
    (BUILD / "reqs.txt").write_text("\n".join(REQS) + "\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--target", str(STAGE / "site-packages"),
                           "--platform", "win_amd64", "--python-version", "3.12", "--implementation", "cp",
                           "--only-binary=:all:", "-r", str(BUILD / "reqs.txt")])

    # 3) Código de la aplicación
    ign = shutil.ignore_patterns("__pycache__", "*.pyc", "tests", ".pytest_cache")
    shutil.copytree(RAIZ / "backend" / "app", STAGE / "backend" / "app", ignore=ign)
    shutil.copytree(RAIZ / "frontend", STAGE / "frontend")
    (STAGE / "desktop").mkdir()
    shutil.copy(AQUI / "launcher.py", STAGE / "desktop" / "launcher.py")
    shutil.copy(AQUI / "respaldo_programado.bat", STAGE / "desktop" / "respaldo_programado.bat")
    shutil.copytree(RAIZ / "db", STAGE / "db")
    shutil.copytree(RAIZ / "datos_prueba", STAGE / "datos_prueba", ignore=shutil.ignore_patterns("reportes_prueba", "__pycache__"))
    (STAGE / "docs").mkdir()
    for m in a.manual:
        shutil.copy(m, STAGE / "docs" / Path(m).name)
    (STAGE / "Iniciar GAM.bat").write_text(
        '@echo off\r\ncd /d "%~dp0desktop"\r\ntitle GAM - Gestion de Personal (cierre esta ventana para detener el sistema)\r\n'
        '"%~dp0python\\python.exe" launcher.py\r\n', encoding="ascii")

    # 4) NSIS
    out = AQUI / "GAMPersonal_Setup.exe"
    subprocess.check_call(["makensis", f"-DVERSION={a.version}", f"-DSTAGE={STAGE}", f"-DOUT={out}", str(AQUI / "installer_simple.nsi")])
    print("\n[OK] Instalador:", out, f"({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
