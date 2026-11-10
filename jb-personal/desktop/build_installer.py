#!/usr/bin/env python3
"""Construye JBPersonal_Setup.exe (instalador de JB-Personal como SERVICIO de Windows) — desde Linux, macOS o Windows.

Empaqueta Python embebido oficial + librerías (wheels win_amd64) + código, y lo envuelve con NSIS. Sin PyInstaller.
Requisitos de la máquina que construye: Python 3.9+, Internet (pypi.org, python.org) y NSIS (`makensis`).
Uso:  python build_installer.py [--version 1.0.0] [--manual archivo ...]
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
REQS_APP = ["fastapi", "uvicorn", "sqlalchemy>=2.0", "python-multipart", "pyjwt", "openpyxl", "python-docx", "reportlab", "cryptography"]


def bajar(url: str, destino: Path):
    if destino.exists():
        return
    print("Descargando", url)
    destino.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, destino)


def preparar_python(stage: Path, reqs: list[str], rutas_extra: str = "..\\backend"):
    """Python embebido + librerías dentro de stage/python y stage/site-packages."""
    zip_py = BUILD / f"python-{PYVER}-embed-amd64.zip"
    bajar(f"https://www.python.org/ftp/python/{PYVER}/python-{PYVER}-embed-amd64.zip", zip_py)
    with zipfile.ZipFile(zip_py) as z:
        z.extractall(stage / "python")
    pth = next((stage / "python").glob("python*._pth"))
    pth.write_text(f"python312.zip\n.\n{rutas_extra}\n..\\site-packages\nimport site\n", encoding="utf-8")
    (BUILD / "reqs.txt").write_text("\n".join(reqs) + "\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--target", str(stage / "site-packages"),
                           "--platform", "win_amd64", "--python-version", "3.12", "--implementation", "cp",
                           "--only-binary=:all:", "-r", str(BUILD / "reqs.txt")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--manual", nargs="*", default=[], help="manuales a incluir (PDF/DOCX)")
    a = ap.parse_args()
    if not shutil.which("makensis"):
        sys.exit("Falta NSIS (makensis). Linux: apt install nsis · Windows: https://nsis.sourceforge.io")
    stage = BUILD / "stage_app"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    preparar_python(stage, REQS_APP)

    ign = shutil.ignore_patterns("__pycache__", "*.pyc", "tests", ".pytest_cache")
    shutil.copytree(RAIZ / "backend" / "app", stage / "backend" / "app", ignore=ign)
    shutil.copytree(RAIZ / "frontend", stage / "frontend")
    (stage / "desktop").mkdir()
    for f in ("launcher.py", "respaldo_programado.bat"):
        shutil.copy(AQUI / f, stage / "desktop" / f)
    shutil.copytree(AQUI / "windows", stage / "desktop" / "windows")
    shutil.copytree(RAIZ / "db", stage / "db")
    shutil.copytree(RAIZ / "datos_prueba", stage / "datos_prueba", ignore=shutil.ignore_patterns("reportes_prueba", "__pycache__"))
    (stage / "docs").mkdir()
    for m in a.manual:
        shutil.copy(m, stage / "docs" / Path(m).name)
    (stage / "LEEME.txt").write_text(
        "JB-Personal - servicio de Windows\r\n"
        "Direccion: http://127.0.0.1:8765/   (acceso directo 'JB-Personal' en el escritorio)\r\n"
        "Datos y respaldos: C:\\ProgramData\\JB-Personal   |   Registro: C:\\ProgramData\\JB-Personal\\logs\\servicio.log\r\n"
        "Administrar (iniciar/detener): menu Inicio > JB-Personal > Administrar el servicio.\r\n", encoding="ascii")

    out = AQUI / "JBPersonal_Setup.exe"
    icon = AQUI / "assets" / "jb-personal.ico"
    subprocess.check_call(["makensis", f"-DVERSION={a.version}", f"-DSTAGE={stage}", f"-DOUT={out}", f"-DICON={icon}",
                           str(AQUI / "installer_jbpersonal.nsi")])
    print("\n[OK] Instalador:", out, f"({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
