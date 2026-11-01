"""Pruebas de interfaz: todas las pantallas se construyen y refrescan sin errores (Qt offscreen)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from tests.conftest import Entorno
from tests.test_reportes import _poblar


@pytest.fixture(autouse=True)
def sin_dialogos_modales(monkeypatch):
    """Un cuadro modal bloquearía la prueba: se convierte en excepción visible."""
    from PySide6.QtWidgets import QMessageBox

    def exec_(self):
        raise AssertionError(f"Se abrió un cuadro de mensaje: {self.windowTitle()}: {self.text()}")
    monkeypatch.setattr(QMessageBox, "exec", exec_)


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    from contabol.ui import tema
    tema.aplicar(a)
    return a


@pytest.fixture
def entorno(app):
    e = Entorno()
    _poblar(e)
    yield e
    e.cerrar()


def test_todas_las_pantallas(app, entorno):
    from contabol.ui.ventana import VentanaPrincipal
    from contabol.ui.p_admin import (AuditoriaPantalla, BackupPantalla, CierrePantalla, ConsolidarPantalla, ParametrosPantalla, UsuariosPantalla, UtilitariosPantalla)
    from contabol.ui.p_comercial import CobrosPagosPantalla, DocumentosPantalla, TercerosPantalla
    from contabol.ui.p_contab import ComprobantesPantalla, ConciliacionPantalla, PlanCuentasPantalla, PresupuestoPantalla, TipoCambioPantalla
    from contabol.ui.p_inventario import CatalogoPantalla, ItemsPantalla, MovimientosPantalla
    from contabol.ui.p_iva import LibroIvaPantalla
    from contabol.ui.p_rrhh import (ActivosPantalla, AnticiposPantalla, BeneficiosPantalla, DepreciacionPantalla, EmpleadosPantalla, PlanillaPantalla, ProduccionPantalla)
    from contabol.ui.reportes_ui import CentroReportes
    from contabol.ui.p_auditoria import AuditoriaFinancieraPantalla as AudFin, AuditoriaTributariaPantalla as AudTrib
    e = entorno
    w = VentanaPrincipal(e.sis, e.usuario, e.ctx)
    w.show()
    casos = [(PlanCuentasPantalla,), (ComprobantesPantalla,), (TipoCambioPantalla,), (ConciliacionPantalla,), (PresupuestoPantalla,), (TercerosPantalla, "C"), (TercerosPantalla, "P"),
             (DocumentosPantalla, True), (DocumentosPantalla, False), (CobrosPagosPantalla,), (ItemsPantalla,), (MovimientosPantalla,), (CatalogoPantalla, "almacen"), (LibroIvaPantalla, "V"),
             (LibroIvaPantalla, "C"), (ActivosPantalla,), (DepreciacionPantalla,), (EmpleadosPantalla,), (PlanillaPantalla,), (AnticiposPantalla,), (BeneficiosPantalla,), (ProduccionPantalla,),
             (ParametrosPantalla,), (AudFin,), (AudTrib,), (UsuariosPantalla,), (AuditoriaPantalla,), (BackupPantalla,), (CierrePantalla,), (ConsolidarPantalla,), (UtilitariosPantalla,), (CentroReportes,)]
    for i, c in enumerate(casos):
        p = w.abrir(c[0], *c[1:], clave=f"t{i}")
        assert p is not None, c
        p.refrescar()
    w.informe("estados_financieros", pedir=False)
    w.informe("balance_general", pedir=False)
    assert w.tabs.count() > 30
    cc = w.abrir(ComprobantesPantalla, clave='cc')
    assert cc.tabla.rowCount() > 0 and cc.d["cbte"].text() and cc.t_lin.rowCount() >= 2
    cc.orden.set_valor("importe")
    cc.refrescar()
    cc.buscar.setText("zzzz-no-existe")
    assert cc.tabla.rowCount() == 0 and cc.d["cbte"].text() == ""
    cc.buscar.setText("")
    pa = w.abrir(AudFin, clave='aud_f')
    assert pa.eid is not None and pa.tabs.count() == 7
    pa._ejecutar_f()
    with pytest.raises(AssertionError, match='aún está abierto'):
        pa.verificar()
    pt = w.abrir(AudTrib, clave='aud_t')
    assert pt.eid is None and pt.cb.count() == 0
    e.ctx.auditoria.crear_encargo('T', 'MAI ui')
    pt.refrescar()
    pt._ejecutar_t()
    pt._depurar()
    pt._gen_anexos()
    pt._borrador()
    w.accion_salida = "cambiar"
    w.close()


def test_dialogos(app, entorno):
    from contabol.ui.p_contab import ComprobanteDialog
    from contabol.ui.p_comercial import DocumentoDialog, CobroDialog
    from contabol.ui.p_inventario import MovimientoDialog
    from contabol.ui.p_iva import FacturaDialog, LiquidacionDialog
    e = entorno
    for d in (ComprobanteDialog(e.ctx, None), ComprobanteDialog(e.ctx, e.ctx.db.scalar("SELECT MIN(id) FROM comprobante")), DocumentoDialog(e.ctx, True), DocumentoDialog(e.ctx, False),
              CobroDialog(e.ctx, "CO"), MovimientoDialog(e.ctx), FacturaDialog(e.ctx, "V"), FacturaDialog(e.ctx, "C"), LiquidacionDialog(e.ctx)):
        d.show()
        d.close()


def test_comprobante_desde_la_grilla(app, entorno):
    from contabol.ui.p_comprobante import ComprobanteDialog
    e = entorno
    d = ComprobanteDialog(e.ctx, None)
    caja, cap = e.ctx.cuentas.por_codigo("1.1.1.01.001"), e.ctx.cuentas.por_codigo("3.1.1.01.001")
    d.tipo.set_valor("T")
    d.grid.poner_linea(0, caja["id"], debe=1000)
    d.grid.poner_linea(1, cap["id"], haber=1000)
    d.glosa.setText("Prueba desde la grilla")
    assert "Cuadra" in d.l_dif.text()
    d.grabar()
    assert d.cid and e.ctx.vouchers.obtener(d.cid)["debe_bs"] == 1000.0
    # escribir códigos como lo haría el usuario
    d2 = ComprobanteDialog(e.ctx, None)
    d2.grid.cellWidget(0, 0).setText("1.1.1.01.001")
    d2.grid.cellWidget(0, 0).editingFinished.emit()
    assert d2.grid.cellWidget(0, 1).text() == "Caja Moneda Nacional"
    d2.grid.cellWidget(0, 3).setText("500")
    d2.grid.cellWidget(0, 3).textEdited.emit("500")
    assert d2.grid.cellWidget(0, 5).text() != ""   # equivalente en US$


def test_igualar_y_calculadora(app, entorno):
    from contabol.ui.calculadora import Calculadora
    from contabol.ui.p_comprobante import ComprobanteDialog
    e = entorno
    d = ComprobanteDialog(e.ctx, None)
    caja = e.ctx.cuentas.por_codigo("1.1.1.01.001")
    d.grid.poner_linea(0, caja["id"], debe=250)
    d.igualar()
    assert d.grid.cellWidget(1, 4).text() == "250,00"
    c = Calculadora()
    c.pantalla.setText("(100+50)/3")
    assert c.calcular() == 50.0


def test_login_restablecer_admin(app, monkeypatch):
    import shutil
    import tempfile
    from PySide6.QtWidgets import QInputDialog
    from contabol.sistema import Sistema
    from contabol.ui.login import LoginDialog
    d = tempfile.mkdtemp()
    try:
        sis = Sistema(d)
        for _ in range(5):
            try:
                sis.autenticar("admin", "x")
            except Exception:  # noqa: BLE001
                pass
        dlg = LoginDialog(sis)
        dlg.u.setText("admin")
        dlg.c.setText("admin")
        dlg.entrar()
        assert "bloqueado" in dlg.err.text()
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("restablecer", True)))
        dlg.restablecer()
        dlg.entrar()
        assert dlg.usuario and dlg.usuario["login"] == "admin"
        sis.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)
