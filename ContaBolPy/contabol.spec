# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller:  pyinstaller contabol.spec --noconfirm
import os
import sys

sys.path.insert(0, os.getcwd())
from PyInstaller.utils.hooks import collect_submodules

# los servicios se cargan dinámicamente (importlib) y deben incluirse explícitamente
hidden = collect_submodules("contabol") + [
    "contabol.services." + m for m in ("cuentas", "tipocambio", "comprobantes", "iva", "terceros", "inventario", "comercial", "activos", "planillas",
                                       "produccion", "presupuesto", "bancos", "libros", "estados", "gestion", "consolidacion")]

a = Analysis(
    ["contabol/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtMultimedia"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="ContaBol",
    console=False,
    icon="scripts/contabol.ico",
    disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ContaBol")
