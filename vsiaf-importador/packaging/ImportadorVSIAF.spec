# -*- mode: python ; coding: utf-8 -*-
# Compilar (en Windows):   pyinstaller packaging\ImportadorVSIAF.spec --noconfirm
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
DATA = [(os.path.join(ROOT, "vsiaf_importer", "data"), os.path.join("vsiaf_importer", "data"))]
HIDDEN = ["openpyxl.cell._writer", "tkinter", "tkinter.ttk", "tkinter.filedialog", "tkinter.messagebox"]
EXCLUDES = ["numpy", "pandas", "matplotlib", "scipy", "PIL", "pytest"]


def analysis(script):
    return Analysis([os.path.join(ROOT, script)], pathex=[ROOT], datas=DATA, hiddenimports=HIDDEN,
                    excludes=EXCLUDES, noarchive=False)


a_gui = analysis("run_importador.py")
a_cli = analysis("run_importador.py")
pyz_gui = PYZ(a_gui.pure)
pyz_cli = PYZ(a_cli.pure)

exe_gui = EXE(pyz_gui, a_gui.scripts, [], exclude_binaries=True, name="ImportadorVSIAF", console=False,
              icon=None, version=None)
exe_cli = EXE(pyz_cli, a_cli.scripts, [], exclude_binaries=True, name="ImportadorVSIAF-consola", console=True)

coll = COLLECT(exe_gui, a_gui.binaries, a_gui.datas, exe_cli, a_cli.binaries, a_cli.datas,
               strip=False, upx=False, name="ImportadorVSIAF")
