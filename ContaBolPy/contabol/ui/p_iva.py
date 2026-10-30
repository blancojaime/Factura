"""Pantallas de impuestos: libros de compras y ventas IVA y liquidación mensual."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from ..util import fdate, fmt, mes_nombre, r2
from . import tema
from .base import ListaCRUD, Pantalla
from .formularios import Campo, FormDialog
from .widgets import CampoFecha, CampoImporte, Columna, Combo, aviso, boton, confirmar, error, etiqueta, hbox, info, intentar

MESES = [(i, mes_nombre(i)) for i in range(1, 13)]


class FacturaDialog(QDialog):
    """Registro de una factura en el libro de compras o ventas, con asiento contable opcional."""

    def __init__(self, ctx, libro: str, parent=None):
        super().__init__(parent)
        self.ctx, self.libro = ctx, libro
        self.setWindowTitle(("Registro de compra" if libro == "C" else "Registro de venta") + " - Factura")
        self.setMinimumWidth(780)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        lay.setSpacing(8)
        h = QLabel("Factura de " + ("compra (crédito fiscal)" if libro == "C" else "venta (débito fiscal)"))
        h.setObjectName("h1")
        lay.addWidget(h)
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        self.fecha = CampoFecha(min(max(date.today(), ctx.inicio), ctx.fin), ctx.inicio, ctx.fin)
        self.nit = QLineEdit()
        self.razon = QLineEdit()
        self.tercero = Combo()
        self.tercero.cargar([(t["id"], f"{t['nombre']} ({t['nit'] or 's/n'})") for t in ctx.terceros.listar("C" if libro == "V" else "P")], "(escribir NIT y razón social)")
        self.nro = QLineEdit()
        self.aut = QLineEdit()
        self.total = CampoImporte(0.0)
        self.nosuj = CampoImporte(0.0)
        self.desc = CampoImporte(0.0)
        self.estado = Combo([("V", "Válida"), ("A", "Anulada"), ("N", "No utilizada"), ("E", "Extraviada")])
        self.base_l, self.iva_l = QLabel("0,00"), QLabel("0,00")
        for l in (self.base_l, self.iva_l):
            l.setStyleSheet(f"font-weight:600; color:{tema.AZUL}; font-size:11pt;")
        filas = [[("Fecha de la factura", self.fecha), ("Cliente/proveedor registrado", self.tercero)],
                 [("NIT / CI", self.nit), ("Razón social", self.razon)],
                 [("Nº de factura", self.nro), ("Nº de autorización / CUF", self.aut)],
                 [("Importe total de la factura", self.total), ("Importe no sujeto a crédito/débito fiscal", self.nosuj)],
                 [("Descuentos y bonificaciones", self.desc), ("Estado", self.estado)]]
        for r, fila in enumerate(filas):
            for c, (et, w) in enumerate(fila):
                g.addWidget(etiqueta(et), r * 2, c)
                g.addWidget(w, r * 2 + 1, c)
        lay.addLayout(g)
        cal = QFrame()
        cal.setObjectName("panel")
        cl = QHBoxLayout(cal)
        cl.setContentsMargins(16, 10, 16, 10)
        cl.addWidget(etiqueta("Importe base:"))
        cl.addWidget(self.base_l)
        cl.addSpacing(30)
        cl.addWidget(etiqueta("Crédito fiscal (13%):" if libro == "C" else "Débito fiscal (13%):"))
        cl.addWidget(self.iva_l)
        cl.addStretch(1)
        lay.addWidget(cal)
        self.asiento = None
        if True:
            from PySide6.QtWidgets import QCheckBox
            self.asiento = QCheckBox("Generar el comprobante contable automáticamente")
            self.asiento.setChecked(True)
            lay.addWidget(self.asiento)
            g2 = QGridLayout()
            self.contra = Combo()
            self.contra.cargar([(c["id"], f"{c['codigo']}  {c['nombre']}") for c in ctx.cuentas.listar(solo_movimiento=True) if c["tipo"] in ("A", "P")], None)
            self.contra.set_valor(ctx.cuenta_por_codigo(ctx.param("CTA_CAJA"))["id"])
            self.cuenta = Combo()
            tipo = "I" if libro == "V" else "G"
            self.cuenta.cargar([(c["id"], f"{c['codigo']}  {c['nombre']}") for c in ctx.cuentas.listar(solo_movimiento=True) if c["tipo"] == tipo or (libro == "C" and c["tipo"] == "A")], None)
            self.cuenta.set_valor(ctx.cuenta_por_codigo(ctx.param("CTA_VENTAS" if libro == "V" else "CTA_REC_COMP"))["id"])
            g2.addWidget(etiqueta("Cuenta de contrapartida (caja, banco o por cobrar/pagar)"), 0, 0)
            g2.addWidget(self.contra, 1, 0)
            g2.addWidget(etiqueta("Cuenta de ingreso" if libro == "V" else "Cuenta de gasto o activo"), 0, 1)
            g2.addWidget(self.cuenta, 1, 1)
            lay.addLayout(g2)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)
        ok, ca = boton("Registrar", "primario", 110), boton("Cancelar", "", 100)
        lay.addLayout(hbox(None, ca, ok))
        ok.clicked.connect(self.guardar)
        ca.clicked.connect(self.reject)
        for w in (self.total, self.nosuj, self.desc):
            w.cambiado.connect(lambda *_: self.calcular())
        self.tercero.currentIndexChanged.connect(self.elegir_tercero)

    def elegir_tercero(self) -> None:
        t = self.ctx.terceros.obtener(self.tercero.valor()) if self.tercero.valor() else None
        if t:
            self.nit.setText(t["nit"] or "")
            self.razon.setText(t["nombre"])

    def datos(self) -> dict:
        return {"libro": self.libro, "fecha": self.fecha.fecha(), "nit": self.nit.text(), "razon_social": self.razon.text(), "nro_factura": self.nro.text(),
                "nro_autorizacion": self.aut.text(), "importe_total": self.total.valor(), "no_sujeto": self.nosuj.valor(), "descuentos": self.desc.valor(),
                "estado": self.estado.valor(), "tercero_id": self.tercero.valor(), "generar_asiento": self.asiento.isChecked(), "contra_cuenta_id": self.contra.valor(),
                "cuenta_id": self.cuenta.valor()}

    def calcular(self) -> None:
        try:
            c = self.ctx.iva.calcular(self.datos())
            self.base_l.setText(fmt(c["base_iva"]))
            self.iva_l.setText(fmt(c["iva"]))
            self.err.setText("")
        except Exception as ex:  # noqa: BLE001
            self.err.setText(str(ex))

    def guardar(self) -> None:
        try:
            self.ctx.iva.registrar(self.datos())
        except Exception as ex:  # noqa: BLE001
            self.err.setText(str(ex)) if hasattr(ex, "args") and not isinstance(ex, (KeyError, TypeError)) else error(self, ex)
            return
        self.accept()


class LiquidacionDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Liquidación mensual de IVA")
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        h = QLabel("Liquidación de IVA e IT")
        h.setObjectName("h1")
        lay.addWidget(h)
        top = QHBoxLayout()
        self.mes = Combo(MESES)
        self.mes.set_valor(min(max(date.today().month if date.today().year == ctx.gestion["anio"] else 12, 1), 12))
        top.addWidget(etiqueta("Mes"))
        top.addWidget(self.mes)
        top.addStretch(1)
        lay.addLayout(top)
        self.cuadro = QLabel("")
        self.cuadro.setTextFormat(Qt.RichText)
        lay.addWidget(self.cuadro)
        lay.addWidget(etiqueta("Cuenta desde la que se paga el IVA"))
        self.cta = Combo()
        self.cta.cargar([(c["id"], f"{c['codigo']}  {c['nombre']}") for c in ctx.bancos.cuentas_banco()], None)
        lay.addWidget(self.cta)
        ok, ca = boton("Generar asiento de liquidación", "primario"), boton("Cerrar")
        lay.addLayout(hbox(None, ca, ok))
        self.mes.currentIndexChanged.connect(self.calc)
        ok.clicked.connect(self.generar)
        ca.clicked.connect(self.reject)
        self.calc()

    def calc(self) -> None:
        r = self.ctx.iva.resumen_mensual(self.ctx.gestion["anio"], self.mes.valor())
        filas = [("Ventas facturadas", r["ventas_facturadas"]), ("Débito fiscal IVA (13%)", r["debito_fiscal"]), ("Compras facturadas", r["compras_facturadas"]),
                 ("Crédito fiscal del mes", r["credito_fiscal"]), ("Saldo de crédito del mes anterior", r["saldo_anterior"]), ("Mantenimiento de valor (UFV)", r["mant_valor"]),
                 ("IVA a pagar (Form. 200)", r["iva_a_pagar"]), ("Saldo a favor para el mes siguiente", r["saldo_favor"]), ("IT devengado (Form. 400)", r["it_devengado"])]
        self.cuadro.setText("<table cellpadding=4 width=100%>" + "".join(f"<tr><td>{a}</td><td align=right><b>{fmt(b)}</b></td></tr>" for a, b in filas) + "</table>")

    def generar(self) -> None:
        if not confirmar(self, "Se generará el comprobante de liquidación del IVA del mes. ¿Continuar?"):
            return
        ok, cid = intentar(self, self.ctx.iva.liquidar, self.ctx.gestion["anio"], self.mes.valor(), self.cta.valor())
        if ok:
            info(self, "Asiento de liquidación generado.")
            self.accept()


class LibroIvaPantalla(ListaCRUD):
    def __init__(self, ctx, libro: str, ventana=None):
        self.libro = libro
        self.titulo = "Libro de compras IVA" if libro == "C" else "Libro de ventas IVA"
        self.subtitulo = ("Registro de facturas de compra: crédito fiscal IVA." if libro == "C" else "Registro de facturas de venta: débito fiscal IVA e IT.")
        self.mes = Combo()
        self.mes.cargar([(0, "Toda la gestión")] + MESES)
        cols = [Columna("fecha", "Fecha", 90, "date"), Columna("nit", "NIT / CI", 110), Columna("razon_social", "Razón social", 230, estirar=True), Columna("nro_factura", "Nº factura", 90),
                Columna("nro_autorizacion", "Autorización / CUF", 150), Columna("importe_total", "Importe total", 110, "money"), Columna("base_iva", "Base", 110, "money"),
                Columna("iva", "Crédito fiscal" if libro == "C" else "Débito fiscal", 110, "money"), Columna("estado_txt", "Estado", 80)]
        acc = [("Nueva factura", self.nueva, "primario"), ("Anular", self.anular, "peligro"), ("Liquidación IVA…", self.liquidar, ""), ("Informe del libro", self.informe, "")]
        super().__init__(ctx, cols, self.datos, acc, True, ventana, colorear=lambda f, c: tema.ROJO if f["estado"] != "V" else None, filtros=[etiqueta("Mes"), self.mes])
        self.mes.currentIndexChanged.connect(lambda *_: self.refrescar())
        self.botones["Nueva factura"].setEnabled(ctx.puede("IVA.REGISTRO") and ctx.abierta)

    def datos(self):
        filas = self.ctx.iva.listar(self.libro, self.ctx.gestion["anio"], self.mes.valor() or None)
        for f in filas:
            f["estado_txt"] = {"V": "Válida", "A": "Anulada", "E": "Extraviada", "N": "No utilizada", "C": "Contingencia"}.get(f["estado"], f["estado"])
        return filas

    def nueva(self, _=None):
        FacturaDialog(self.ctx, self.libro, self.ventana or self).exec()

    def anular(self, f):
        if f and confirmar(self, f"¿Anular la factura {f['nro_factura']}?", "Anular", True):
            self.ctx.iva.anular(f["id"])

    def liquidar(self, _=None):
        LiquidacionDialog(self.ctx, self.ventana or self).exec()

    def informe(self, _=None):
        self.ventana.informe("libro_compras" if self.libro == "C" else "libro_ventas")
