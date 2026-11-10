import os as _os
import sys as _sys

if _sys.platform.startswith("win") and _os.environ.get("SICOM_GTK_DIR"):  # Pango empaquetado: debe fijarse antes de importar WeasyPrint
    _os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", _os.environ["SICOM_GTK_DIR"])
