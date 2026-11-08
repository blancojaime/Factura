# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: ejecutar desde la carpeta desktop\  ->  pyinstaller gam_personal.spec --noconfirm
from PyInstaller.utils.hooks import collect_submodules

hidden = (collect_submodules("uvicorn") + collect_submodules("sqlalchemy.dialects") + collect_submodules("app")
          + ["multipart", "openpyxl", "docx", "reportlab", "cryptography", "jwt", "webview"])
a = Analysis(
    ["launcher.py"],
    pathex=["../backend"],
    datas=[("../frontend", "frontend"), ("../backend/app/templates", "app/templates")],
    hiddenimports=hidden,
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="GAMPersonal", console=False, icon=None)
coll = COLLECT(exe, a.binaries, a.datas, name="GAMPersonal")
