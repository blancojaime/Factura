# PyInstaller: genera dist/SIIM2026/SIIM2026.exe (carpeta, más estable y rápida de arrancar que "un solo archivo")
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
block_cipher = None
datas = [("siim/data/seed.json", "siim/data"), ("siim/resources", "siim/resources")]
a = Analysis(["run.py"], pathex=["."], datas=datas, hiddenimports=collect_submodules("reportlab.graphics.barcode") + collect_submodules("reportlab.graphics.charts"),
             excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "matplotlib", "numpy.tests"],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SIIM2026", console=False, icon="siim/resources/icon.ico", disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="SIIM2026")
