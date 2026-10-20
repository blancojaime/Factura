# Importador Excel → VSIAF 2.0

Aplicación de escritorio (Windows) que importa activos fijos, revalúos, transferencias y bajas desde un libro Excel
a la base de datos FoxPro del **VSIAF 2.0** (Ministerio de Economía y Finanzas Públicas de Bolivia), con validación,
vista previa de cálculo (UFV / depreciación), respaldo automático y reversión si algo falla.

* Guía completa: [GUIA_DE_USO.md](GUIA_DE_USO.md) (también `GUIA_DE_USO.docx`).
* Python 3.12 · Tkinter · openpyxl · PyInstaller · Inno Setup.

```
vsiaf_importer/      código (dbf.py, ufv.py, calc.py, importer.py, excelio.py, gui.py, cli.py…)
tests/               pruebas (pytest); tests/test_sample_db.py usa una instalación real si VSIAF_SAMPLE_DIR está definida
packaging/           ImportadorVSIAF.spec (PyInstaller), instalador.iss (Inno Setup), build_windows.bat
```

## Uso rápido

```
pip install -r requirements.txt
python run_importador.py                       # abre la ventana
python run_importador.py plantilla libro.xlsx --ejemplos
python run_importador.py validar libro.xlsx --vsiaf C:\vsiaf --unidad 1
python run_importador.py importar libro.xlsx --vsiaf C:\vsiaf --unidad 1
```

Después de importar: **abrir el VSIAF → Administradores → Re-indexar**.

## Desarrollo

```
pip install -r requirements-dev.txt
pytest -q tests
# con una instalación real (copia):  VSIAF_SAMPLE_DIR=/ruta/a/vsiaf pytest -q tests
```

Compilar el instalador en Windows: `packaging\build_windows.bat` (o el flujo *Importador VSIAF (Windows)* de GitHub Actions).
