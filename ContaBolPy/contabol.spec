# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller:  pyinstaller contabol.spec --noconfirm
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("contabol")

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
