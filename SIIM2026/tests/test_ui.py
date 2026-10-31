"""Pruebas de interfaz sin pantalla (QT_QPA_PLATFORM=offscreen): todas las pantallas se construyen y los flujos principales funcionan."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QDialog

from siim.core import license as Lic
from siim.reports import catalogo
from siim.ui import widgets
from siim.ui.main_window import AppState, MainWindow
from siim.services import liquidacion as L


@pytest.fixture(scope="module")
def qapp():
    from siim.ui import theme
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(theme.QSS)
    return a


@pytest.fixture()
def win(qapp, db, ctx, ids, monkeypatch):
    opened = []
    import sys
    def _boom(parent, msg, *a, **k):
        raise AssertionError("Diálogo de error mostrado: " + str(msg))
    import siim.ui.main_window, siim.ui.liquidacion, siim.ui.recaudacion, siim.ui.padron, siim.ui.reportes, siim.ui.otros, siim.ui.actividades, siim.ui.mantenimiento  # noqa
    for name, mod in list(sys.modules.items()):
        if name.startswith("siim.ui"):
            for attr, fn in (("open_file", lambda p: opened.append(str(p))), ("info", lambda *a, **k: None), ("confirm", lambda *a, **k: True), ("error", _boom)):
                if hasattr(mod, attr):
                    monkeypatch.setattr(mod, attr, fn)
    st = AppState(db, ctx.session, Lic.LicenseManager(db))
    w = MainWindow(st)
    w.opened = opened
    w.ids = ids
    return w


def test_todas_las_pantallas(win, qapp):
    for i in range(win.nav.count()):
        win.nav.setCurrentRow(i)
        qapp.processEvents()
    assert win.nav.count() == 10


def test_flujo_liquidacion_individual_y_cobro(win, qapp):
    win.nav.setCurrentRow(3)
    from siim.ui.liquidacion import Individual
    pg = win.stack.currentWidget().findChild(Individual)
    pg.pmcbox.set(win.ids["perez"])
    pg.objs.selectRow(0)
    pg.calcular()
    assert pg.pre["neto"] > 0 and pg.b_emit.isEnabled()
    pg.emitir()
    assert any(p.endswith(".pdf") for p in win.opened)
    from siim.ui.recaudacion import Cobro
    win.nav.setCurrentRow(4)
    cb = win.stack.currentWidget().findChild(Cobro)
    cb.modo.setCurrentIndex(0)
    cb.txt.setText(str(win.ids["perez"]))
    cb.buscar()
    assert cb.t.rows
    cb.t.selectRow(0)
    cb.fecha.form.set("fecha", "2005-03-30")
    cb.calcular()
    assert cb.d["descuento"] > 0
    cb.cobrar()
    assert win.app.db.scalar("SELECT COUNT(*) FROM pagos WHERE estado='VIGENTE'") == 1


def test_todos_los_reportes_en_pantalla(win):
    from siim.ui.reportes import ReportesPage
    win.nav.setCurrentRow(6)
    pg = win.stack.currentWidget()
    assert isinstance(pg, ReportesPage)
    top = pg.tree.topLevelItemCount()
    n = 0
    for i in range(top):
        g = pg.tree.topLevelItem(i)
        for j in range(g.childCount()):
            k = g.child(j).data(0, 256)
            if catalogo.CATALOGO[k]["params"] and any(p["kind"] == "pmc" for p in catalogo.CATALOGO[k]["params"]):
                continue
            pg.tree.setCurrentItem(g.child(j))
            pg.generar()
            assert pg.rep is not None
            n += 1
    assert n >= 35


def test_dialogo_contribuyente_y_objetos(win, qapp):
    from siim.ui.padron import ContribuyenteDialog, ObjetoDialog
    d = ContribuyenteDialog(win.app, "F-027", win.ids["perez"], "77")
    assert d.tabs.isTabEnabled(1)
    for t in ("inmuebles", "vehiculos", "actividades", "publicidad"):
        ObjetoDialog(win.app, t)
    d2 = ContribuyenteDialog(win.app, "F-019", None, "1")
    d2.form.set("nro_doc", "99887766"); d2.form.set("paterno", "Nuevo"); d2.form.set("nombre", "Cliente"); d2.form.set("calle", "X")
    d2.guardar()
    assert d2.pmc and d2.tabs.isTabEnabled(1)


def test_editor_tablas_mantenimiento(win):
    from siim.ui.mantenimiento import TABLAS, TableEditor
    for k in TABLAS:
        e = TableEditor(win.app, k)
        assert e.tabla.columnCount() == len(TABLAS[k]["campos"])


def test_arranque_completo_primer_uso(qapp, tmp_path, monkeypatch):
    """Recorre siim.main.run(): configuración inicial → activación (prueba) → ingreso → ventana principal."""
    monkeypatch.setenv("SIIM_HOME", str(tmp_path))
    from PySide6.QtWidgets import QDialog
    from siim import main as M
    from siim.core import security
    from siim.ui import acceso

    vistos = []

    def fake_exec(self):
        n = type(self).__name__
        vistos.append(n)
        if n == "FirstRun":
            self.datos = ("GAM Prueba", "Admin", "admin", "Clave2026x")
        elif n == "Login":
            self.session = security.login(self.db, "admin", "Clave2026x")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    monkeypatch.setattr(QApplication, "exec", lambda *a: 0)
    monkeypatch.setattr("siim.ui.main_window.MainWindow.show", lambda self: None)
    monkeypatch.setattr("PySide6.QtWidgets.QApplication.__init__", lambda self, *a, **k: None) if False else None
    import sys
    monkeypatch.setattr(sys, "argv", ["siim"])
    assert M.run() == 0
    assert "FirstRun" in vistos and "Login" in vistos
