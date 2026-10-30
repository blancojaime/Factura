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
    e = entorno
    w = VentanaPrincipal(e.sis, e.usuario, e.ctx)
    w.show()
    casos = [(PlanCuentasPantalla,), (ComprobantesPantalla,), (TipoCambioPantalla,), (ConciliacionPantalla,), (PresupuestoPantalla,), (TercerosPantalla, "C"), (TercerosPantalla, "P"),
             (DocumentosPantalla, True), (DocumentosPantalla, False), (CobrosPagosPantalla,), (ItemsPantalla,), (MovimientosPantalla,), (CatalogoPantalla, "almacen"), (LibroIvaPantalla, "V"),
             (LibroIvaPantalla, "C"), (ActivosPantalla,), (DepreciacionPantalla,), (EmpleadosPantalla,), (PlanillaPantalla,), (AnticiposPantalla,), (BeneficiosPantalla,), (ProduccionPantalla,),
             (ParametrosPantalla,), (UsuariosPantalla,), (AuditoriaPantalla,), (BackupPantalla,), (CierrePantalla,), (ConsolidarPantalla,), (UtilitariosPantalla,), (CentroReportes,)]
    for i, c in enumerate(casos):
        p = w.abrir(c[0], *c[1:], clave=f"t{i}")
        assert p is not None, c
        p.refrescar()
    w.informe("estados_financieros", pedir=False)
    w.informe("balance_general", pedir=False)
    assert w.tabs.count() > 30
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
    from contabol.ui.p_contab import ComprobanteDialog
    from PySide6.QtCore import Qt
    e = entorno
    d = ComprobanteDialog(e.ctx, None)
    caja, cap = e.ctx.cuentas.por_codigo("1.1.1.01.001"), e.ctx.cuentas.por_codigo("3.1.1.01.001")
    g = d.grid
    for r, (c, deb, hab) in enumerate([(caja, "1.000,00", ""), (cap, "", "1.000,00")]):
        g.item(r, 0).setText(f"{c['codigo']}  {c['nombre']}")
        g.item(r, 0).setData(Qt.UserRole, c["id"])
        g.item(r, 2).setText(deb)
        g.item(r, 3).setText(hab)
    d.glosa.setText("Prueba desde la grilla")
    d.guardar()
    assert d.cid and e.ctx.vouchers.obtener(d.cid)["debe_bs"] == 1000.0
