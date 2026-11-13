# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller:  pyinstaller contabol.spec --noconfirm
import os
import sys

sys.path.insert(0, os.getcwd())
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# los servicios se cargan dinámicamente (importlib) y deben incluirse explícitamente
hidden = collect_submodules("contabol") + [
    "contabol.services." + m for m in ("cuentas", "tipocambio", "comprobantes", "iva", "terceros", "inventario", "comercial", "activos", "planillas",
                                       "produccion", "presupuesto", "bancos", "libros", "estados", "gestion", "consolidacion", "auditoria", "auditoria_plantillas", "auditoria_pruebas", "auditoria_tributaria", "auditoria_informes")] + ["contabol.api", "contabol.reports.word", "contabol.licencia", "docx", "cryptography"]

a = Analysis(
    ["contabol/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[("contabol/recursos", "contabol/recursos")] + collect_data_files("docx"),
    hiddenimports=hidden,
    excludes=["tkinter"] + [q + m for q in ("PySide6.", "PySide2.") for m in ("QtWebEngineCore", "QtWebEngineWidgets", "QtQml", "QtQuick", "Qt3DCore", "QtMultimedia", "QtCharts", "QtDataVisualization")],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="ContaJB",
    console=False,
    icon="scripts/contabol.ico",
    disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ContaJB")
