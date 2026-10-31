"""Genera capturas de pantalla (modo sin pantalla) con datos de demostración para los manuales. Uso: python tools/capturas.py <carpeta_salida>"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["SIIM_HOME"] = tempfile.mkdtemp()

from PySide6.QtWidgets import QApplication, QTabWidget

from siim.core import demo, security, seed
from siim.core import license as Lic
from siim.core.db import Database
from siim.core.paths import db_path
from siim.services import liquidacion as L
from siim.services import recaudacion as R
from siim.services.base import Ctx
from siim.ui import theme
from siim.ui.main_window import AppState, MainWindow


def montar():
    db = Database(db_path())
    seed.seed_base(db)
    demo.cargar_cotizaciones_demo(db)
    security.create_user(db, "admin", "Administrador del sistema", "ADMINISTRADOR", "Clave2026x")
    ses = security.login(db, "admin", "Clave2026x")
    ctx = Ctx(db, ses)
    ids = demo.cargar_padron_demo(ctx)
    L.liquidar_masiva(ctx, "IPBI", 2004, guardar=True)
    L.liquidar_masiva(ctx, "PAF", 2004, guardar=True)
    for lid in [r[0] for r in db.all("SELECT id FROM liquidaciones WHERE rubro='IPBI' LIMIT 3")]:
        R.cobrar(ctx, lid, "2005-03-30")
    db.set_param("ultimo_backup", "2099-01-01T00:00:00")
    return db, ses, ids


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyleSheet(theme.QSS)
    db, ses, ids = montar()
    st = AppState(db, ses, Lic.LicenseManager(db))
    w = MainWindow(st)
    w.resize(1360, 820); w.show()
    for i in range(w.nav.count()):
        w.nav.setCurrentRow(i)
        app.processEvents()
        nombre = w.nav.item(i).text()
        pg = w.stack.currentWidget()
        w.grab().save(str(out / f"{i:02d}_{nombre.split()[0].lower()}.png"))
        for t in pg.findChildren(QTabWidget):
            if t.parent() is pg or t.parentWidget() is pg:
                for k in range(t.count()):
                    t.setCurrentIndex(k); app.processEvents()
                    w.grab().save(str(out / f"{i:02d}_{nombre.split()[0].lower()}_tab{k}.png"))
                t.setCurrentIndex(0)
    print("capturas:", len(list(out.glob('*.png'))))
    db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "capturas")
