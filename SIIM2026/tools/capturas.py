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


def montar(masiva=True):
    db = Database(db_path())
    seed.seed_base(db)
    demo.cargar_cotizaciones_demo(db)
    security.create_user(db, "admin", "Administrador del sistema", "ADMINISTRADOR", "Clave2026x")
    ses = security.login(db, "admin", "Clave2026x")
    ctx = Ctx(db, ses)
    ids = demo.cargar_padron_demo(ctx)
    if masiva:
        L.liquidar_masiva(ctx, "IPBI", 2004, guardar=True)
        L.liquidar_masiva(ctx, "PAF", 2004, guardar=True)
        for lid in [r[0] for r in db.all("SELECT id FROM liquidaciones WHERE rubro='IPBI' LIMIT 3")]:
            R.cobrar(ctx, lid, "2005-03-30")
    else:
        L.liquidar(ctx, "IPBI", ids["inm_lopez"], 2004)
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
    sys.stdout.flush()
    os._exit(0)




def _boom(parent, msg, *a, **k):
    raise RuntimeError("DIALOGO DE ERROR: " + str(msg))


def escenarios(out):
    """Capturas con los datos ya cargados y acciones simuladas, para los manuales."""
    from PySide6.QtWidgets import QWidget
    from siim.ui import widgets
    from siim.ui.acceso import Activacion, FirstRun, Login
    from siim.ui.actividades import Simulador
    from siim.ui.liquidacion import Individual
    from siim.ui.mantenimiento import ParametrosPage, TableEditor
    from siim.ui.otros import FucNuevo
    from siim.ui.padron import ContribuyenteDialog, ObjetoDialog
    from siim.ui.recaudacion import Cobro
    from siim.ui.reportes import Calculadora, ReportesPage, Utilitarios
    for m in list(sys.modules.values()):
        if getattr(m, "__name__", "").startswith("siim.ui"):
            for a, f in (("info", lambda *a, **k: None), ("confirm", lambda *a, **k: True), ("open_file", lambda p: None), ("error", _boom)):
                if hasattr(m, a):
                    setattr(m, a, f)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.QSS)
    db, ses, ids = montar(False)
    st = AppState(db, ses, Lic.LicenseManager(db))
    w = MainWindow(st); w.resize(1360, 820); w.show()
    shot = lambda widget, name: (app.processEvents(), widget.grab().save(str(out / f"{name}.png")))
    ir = lambda nombre: [w.nav.setCurrentRow(i) for i in range(w.nav.count()) if w.nav.item(i).text().startswith(nombre)] and app.processEvents()
    # inicio
    ir("Inicio"); shot(w, "inicio")
    # login / activación / primer uso
    d = Login(db, db.param("municipio")); d.show(); shot(d, "login")
    d = Activacion(st.lic, st.lic.status(), True); d.show(); shot(d, "activacion")
    d = FirstRun(); d.show(); shot(d, "primer_uso")
    # padrón y diálogos
    ir("Empadronamiento"); shot(w, "padron")
    d = ContribuyenteDialog(st, "F-027", ids["perez"], "F027-0045"); d.show(); shot(d, "contribuyente")
    d.tabs.setCurrentIndex(1); shot(d, "contribuyente_inmuebles")
    o = ObjetoDialog(st, "inmuebles", db.one("SELECT * FROM inmuebles WHERE id=?", (ids["inm_perez"],))); o.show(); shot(o, "dlg_inmueble")
    o = ObjetoDialog(st, "actividades", db.one("SELECT * FROM actividades WHERE id=?", (ids["act_farm"],))); o.show(); shot(o, "dlg_actividad")
    o = ObjetoDialog(st, "vehiculos", db.one("SELECT * FROM vehiculos WHERE id=?", (ids["veh_perez"],))); o.show(); shot(o, "dlg_vehiculo")
    # liquidación
    ir("Liquidación"); pg = w.stack.currentWidget().findChild(Individual)
    pg.pmcbox.set(ids["perez"]); pg.objs.selectRow(0); pg.calcular(); shot(w, "liq_ipbi")
    pg.rubro.setCurrentIndex(2); pg.pmcbox.set(ids["farmacia"]); pg.objs.selectRow(0); pg.calcular(); shot(w, "liq_paf")
    pg.rubro.setCurrentIndex(1); pg.pmcbox.set(ids["perez"]); pg.objs.selectRow(0); pg.calcular(); shot(w, "liq_ipva")
    # recaudación
    ir("Recaudación"); cb = w.stack.currentWidget().findChild(Cobro)
    cb.modo.setCurrentIndex(0); cb.txt.setText(str(ids["lopez"])); cb.buscar(); cb.t.selectRow(0); cb.fecha.form.set("fecha", "2005-03-30"); cb.calcular(); shot(w, "cobro_descuento")
    cb.fecha.form.set("fecha", "2005-06-30"); cb.calcular(); shot(w, "cobro_mora")
    # actividades: simulador
    ir("Actividades"); sim = w.stack.currentWidget().findChild(Simulador)
    sim.form.set("zona", "1"); sim.form.set("superficie", 45); sim.form.set("fecha_inicio", "2001-03-15"); sim.form.set("act", "14"); sim._cats(); sim.form.set("cat", "05"); sim.simular()
    w.stack.currentWidget().findChild(QTabWidget).setCurrentIndex(2); shot(w, "act_simulador")
    w.stack.currentWidget().findChild(QTabWidget).setCurrentIndex(0); shot(w, "act_licencias")
    # otros ingresos
    ir("Otros"); fn = w.stack.currentWidget().findChild(FucNuevo)
    fn.f.form.set("nombre", "Juan Quispe Mamani"); fn.f.form.set("detalle", "Legalizaciones y sentaje de feria")
    for cod, c in (("151003.002", 10), ("153401.002", 3), ("151003.001", 1)):
        fn.sub.setCurrentIndex(fn.sub.findData(cod)); fn.cant.form.set("cant", c); fn.agregar()
    shot(w, "fuc")
    # reportes
    ir("Reportes"); rp = w.stack.currentWidget()
    from PySide6.QtCore import Qt as _Qt
    for i in range(rp.tree.topLevelItemCount()):
        g = rp.tree.topLevelItem(i)
        for j in range(g.childCount()):
            if g.child(j).data(0, _Qt.UserRole) == "act_proyeccion":
                rp.tree.setCurrentItem(g.child(j))
    rp.generar(); shot(w, "reportes")
    # deuda
    ir("Deuda"); ca = w.stack.currentWidget()
    ca.form.set("to", 1000); ca.form.set("fv", "2004-12-31"); ca.form.set("fp", "2005-04-21"); ca.form.set("auto", False); ca.form.set("ufv_fv", 1.08593); ca.form.set("ufv_fp", 1.10293); ca.form.set("r", 0.1082); ca.form.set("modo", "SIIM_PDF")
    ca.calc(); shot(w, "deuda")
    # mantenimiento
    ir("Mantenimiento"); mp = w.stack.currentWidget(); shot(w, "mant_parametros")
    mp.findChild(QTabWidget).setCurrentIndex(5); shot(w, "mant_ipva")
    mp.findChild(QTabWidget).setCurrentIndex(6); shot(w, "mant_patentes")
    ir("Utilitarios"); u = w.stack.currentWidget(); u.app.hacer_backup("demo"); u.cargar_b(); shot(w, "backups")
    u.findChild(QTabWidget).setCurrentIndex(4); shot(w, "licencia")
    print("escenarios:", len(list(out.glob("*.png"))))
    db.close()
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "escenarios":
        escenarios(sys.argv[1])
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else "capturas")
