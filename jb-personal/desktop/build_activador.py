#!/usr/bin/env python3
"""Construye JBActivador_Setup.exe (herramienta del EMISOR de licencias).

  python build_activador.py --clave-privada ruta/clave_privada.pem     (la incluye: el instalador queda listo para usar)
  python build_activador.py                                            (sin clave: al primer uso genera una NUEVA y avisa;
                                                                         habrá que incorporar su clave pública a la aplicación)
¡El instalador con clave privada NO debe publicarse ni subirse a repositorios!
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from build_installer import AQUI, BUILD, RAIZ, preparar_python


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clave-privada")
    ap.add_argument("--version", default="1.0.0")
    a = ap.parse_args()
    stage = BUILD / "stage_activador"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    preparar_python(stage, ["cryptography"], rutas_extra=".")
    shutil.copy(RAIZ / "activador" / "jb_activador.py", stage / "jb_activador.py")
    if a.clave_privada:
        shutil.copy(a.clave_privada, stage / "clave_privada.pem")
    out = AQUI / ("JBActivador_Setup.exe")
    subprocess.check_call(["makensis", f"-DVERSION={a.version}", f"-DSTAGE={stage}", f"-DOUT={out}",
                           f"-DICON={AQUI / 'assets' / 'jb-personal.ico'}", str(AQUI / "installer_activador.nsi")])
    print("[OK]", out, "(con clave privada)" if a.clave_privada else "(sin clave)")


if __name__ == "__main__":
    main()
