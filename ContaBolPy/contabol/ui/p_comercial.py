"""Pantallas comerciales: clientes/proveedores, notas de venta y compra, cobros y pagos."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemDelegate, QAbstractItemView, QCheckBox, QCompleter, QDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout)

from ..sistema import ErrorNegocio
from ..util import fdate, fmt, monto_en_letras, parse_num, r2
from . import tema
from .base import ListaCRUD, Pantalla
from .formularios import Campo, FormDialog
from .p_contab import ImporteDelegate
from .widgets import CampoFecha, CampoImporte, Columna, Combo, aviso, boton, confirmar, error, etiqueta, hbox, info, intentar


# ===================================================================== terceros
class TercerosPantalla(ListaCRUD):
    def __init__(self, ctx, clase: str, ventana=None):
        self.clase = clase
        self.titulo = "Clientes" if clase == "C" else "Proveedores"
        self.subtitulo = ("Clientes con límite y días de crédito." if clase == "C" else "Proveedores y acreedores comerciales.")
        cols = [Columna("codigo", "Código", 90), Columna("nombre", "Nombre / razón social", 260, estirar=True), Columna("nit", "NIT / CI", 110), Columna("telefono", "Teléfono", 110),
                Columna("email", "Correo", 170), Columna("limite_credito", "Límite crédito", 110, "money"), Columna("dias_credito", "Días", 60, "int"), Columna("saldo", "Saldo Bs", 110, "money")]
        super().__init__(ctx, cols, self.datos, [("Nuevo", self.editar, "primario"), ("Modificar", self.editar, ""), ("Eliminar", self.eliminar, "peligro"), ("Estado de cuenta", self.estado, "")],
                         True, ventana, doble_clic=self.editar)

    def datos(self):
        filas = self.ctx.terceros.listar(self.clase, solo_activos=False)
        for f in filas:
            f["saldo"] = self.ctx.terceros.saldo(f["id"], self.clase)
        return filas

    def editar(self, f=None):
        nuevo = not f or not isinstance(f, dict) or "id" not in f
        v = dict(f) if not nuevo else {"clase": self.clase, "activo": 1}
        campos = [Campo("codigo", "Código (automático si se deja vacío)"), Campo("nit", "NIT / CI"), Campo("nombre", "Nombre o razón social", "txt", True, ancho=2),
                  Campo("direccion", "Dirección", ancho=2), Campo("telefono", "Teléfono"), Campo("email", "Correo electrónico"), Campo("contacto", "Persona de contacto"),
                  Campo("limite_credito", "Límite de crédito (Bs)", "money"), Campo("dias_credito", "Días de crédito", "int"), Campo("activo", "Activo", "check")]

        def guardar(x):
            x["id"] = None if nuevo else f["id"]
            x["clase"] = v["clase"]
            self.ctx.terceros.guardar(x)
        FormDialog("Cliente" if self.clase == "C" else "Proveedor", campos, v, guardar, parent=self.ventana or self).exec()

    def eliminar(self, f):
        if f and confirmar(self, f"¿Eliminar a {f['nombre']}?", peligro=True):
            self.ctx.terceros.eliminar(f["id"])

    def estado(self, f):
        if f and self.ventana:
            self.ventana.informe("kardex_tercero", {"clase": self.clase, "tercero": f["id"], "desde": self.ctx.inicio, "hasta": self.ctx.fin}, pedir=False)


# ================================================================ documentos
class ItemDelegate(QStyledItemDelegate):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.textos = [f"{i['codigo']}  {i['nombre']}" for i in items]

    def createEditor(self, parent, option, index):
        e = QLineEdit(parent)
        c = QCompleter(self.textos, e)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.setFilterMode(Qt.MatchContains)
        e.setCompleter(c)
        return e

    def setEditorData(self, editor, index):
        editor.setText(index.data(Qt.EditRole) or "")

    def setModelData(self, editor, model, index):
        t = editor.text().strip()
        it = self.resolver(t)
        model.setData(index, f"{it['codigo']}  {it['nombre']}" if it else t, Qt.EditRole)
        model.setData(index, it["id"] if it else None, Qt.UserRole)

    def resolver(self, t):
        tl = t.lower()
        for i in self.items:
            if tl in (i["codigo"].lower(), f"{i['codigo']}  {i['nombre']}".lower()):
                return i
        cand = [i for i in self.items if tl and (tl in i["nombre"].lower() or i["codigo"].lower().startswith(tl))]
        return cand[0] if len(cand) == 1 else None


class GridItems(QTableWidget):
    cambio = Signal()

    def __init__(self, ctx, venta: bool, filas: int = 7):
        super().__init__(filas, 5)
        self.ctx, self.venta = ctx, venta
        self.setHorizontalHeaderLabels(["Ítem (código o nombre)", "Cantidad", "Precio unit.", "Descuento", "Importe"])
        h = self.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in ((1, 100), (2, 120), (3, 110), (4, 130)):
            self.setColumnWidth(i, w)
        self.verticalHeader().setDefaultSectionSize(30)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.deleg = ItemDelegate(ctx.inventario.items())
        self.setItemDelegateForColumn(0, self.deleg)
        for c in (1, 2, 3):
            self.setItemDelegateForColumn(c, ImporteDelegate(self))
        self._b = False
        self.itemChanged.connect(self._cambio)
        for r in range(filas):
            self._fila(r)

    def _fila(self, r: int) -> None:
        self._b = True
        for c in range(5):
            if not self.item(r, c):
                it = QTableWidgetItem("")
                if c:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c == 4:
                    it.setFlags(Qt.ItemIsEnabled)
                self.setItem(r, c, it)
        self._b = False

    def _cambio(self, it):
        if self._b:
            return
        r, c = it.row(), it.column()
        self._b = True
        if c == 0:
            idx = it.data(Qt.UserRole)
            if idx:
                item = self.ctx.inventario.item(idx)
                if not self.item(r, 1).text():
                    self.item(r, 1).setText("1,00")
                precio = item["precio_venta"] if self.venta else item["costo_prom"]
                self.item(r, 2).setText(fmt(precio))
            it.setForeground(QColor(tema.ROJO if it.text() and not idx else tema.TEXTO))
        cant, pr, de = (parse_num(self.item(r, k).text()) for k in (1, 2, 3))
        self.item(r, 4).setText(fmt(cant * pr - de) if cant and pr else "")
        self._b = False
        if r == self.rowCount() - 1 and self.item(r, 0).text():
            self.insertRow(self.rowCount())
            self._fila(self.rowCount() - 1)
        self.cambio.emit()

    def closeEditor(self, editor, hint):
        super().closeEditor(editor, hint)
        if hint in (QAbstractItemDelegate.SubmitModelCache, QAbstractItemDelegate.NoHint):
            r, c = self.currentRow(), self.currentColumn()
            if c < 3:
                self.setCurrentCell(r, c + 1)
            else:
                self.setCurrentCell(min(r + 1, self.rowCount() - 1), 0)

    def lineas(self) -> list[dict]:
        out = []
        for r in range(self.rowCount()):
            idx = self.item(r, 0).data(Qt.UserRole)
            if not idx:
                continue
            out.append({"item_id": idx, "cantidad": parse_num(self.item(r, 1).text()), "precio": parse_num(self.item(r, 2).text()), "descuento": parse_num(self.item(r, 3).text())})
        return out

    def quitar(self) -> None:
        r = self.currentRow()
        if r >= 0 and self.rowCount() > 1:
            self.removeRow(r)
            self.cambio.emit()


class DocumentoDialog(QDialog):
    """Nota de venta o de compra con contabilización automática."""

    def __init__(self, ctx, venta: bool, parent=None):
        super().__init__(parent)
        self.ctx, self.venta = ctx, venta
        self.vent = parent
        self.setWindowTitle("Nota de venta" if venta else "Nota de compra")
        self.resize(1020, 700)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        lay.setSpacing(8)
        h = QLabel("Nota de venta" if venta else "Nota de compra")
        h.setObjectName("h1")
        lay.addWidget(h)
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        self.fecha = CampoFecha(min(max(date.today(), ctx.inicio), ctx.fin), ctx.inicio, ctx.fin)
        self.tercero = Combo()
        self.tercero.cargar([(t["id"], f"{t['nombre']}  ({t['nit'] or 's/n'})") for t in ctx.terceros.listar("C" if venta else "P")], "Seleccione…")
        self.pago = Combo([("CON", "Contado"), ("CRE", "Crédito")])
        self.almacen = Combo([(a["id"], a["nombre"]) for a in ctx.inventario.catalogo("almacen")])
        self.vend = Combo()
        self.vend.cargar([(v["id"], v["nombre"]) for v in ctx.inventario.catalogo("vendedor")], "(sin vendedor)")
        self.con_fac = QCheckBox("Con factura")
        self.con_fac.setChecked(True)
        self.nro = QLineEdit()
        self.nro.setPlaceholderText("Nº factura")
        self.aut = QLineEdit()
        self.aut.setPlaceholderText("Autorización / CUF")
        self.cuenta = Combo()
        self.cuenta.cargar([(c["id"], f"{c['codigo']}  {c['nombre']}") for c in ctx.bancos.cuentas_banco()], None)
        self.cuenta.set_valor(ctx.cuenta_por_codigo(ctx.param("CTA_CAJA"))["id"])
        filas = [[("Fecha", self.fecha), ("Cliente" if venta else "Proveedor", self.tercero), ("Condición de pago", self.pago), ("Almacén", self.almacen)],
                 [("Nº factura", self.nro), ("Autorización / CUF", self.aut), ("Cuenta de caja o banco", self.cuenta), ("Vendedor" if venta else "", self.vend if venta else QLabel(""))]]
        for r, fila in enumerate(filas):
            for c, (et, w) in enumerate(fila):
                g.addWidget(etiqueta(et), r * 2, c)
                g.addWidget(w, r * 2 + 1, c)
        g.addWidget(self.con_fac, 4, 0)
        lay.addLayout(g)
        self.grid = GridItems(ctx, venta)
        lay.addWidget(self.grid, 1)
        b = QHBoxLayout()
        bq = boton("− Quitar línea")
        b.addWidget(bq)
        b.addStretch(1)
        self.desc = CampoImporte(0.0)
        self.desc.setMaximumWidth(110)
        self.rec = CampoImporte(0.0)
        self.rec.setMaximumWidth(110)
        self.cuenta_pag = CampoImporte(0.0)
        self.cuenta_pag.setMaximumWidth(110)
        for et, w in (("Descuento", self.desc), ("Recargo", self.rec), ("A cuenta", self.cuenta_pag)):
            b.addWidget(etiqueta(et))
            b.addWidget(w)
        lay.addLayout(b)
        self.l_tot = QLabel("")
        self.l_tot.setStyleSheet("font-size:12pt; font-weight:600;")
        self.l_tot.setAlignment(Qt.AlignRight)
        lay.addWidget(self.l_tot)
        self.l_let = QLabel("")
        self.l_let.setObjectName("sub")
        self.l_let.setAlignment(Qt.AlignRight)
        lay.addWidget(self.l_let)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)
        ok, ca = boton("Registrar", "primario", 130), boton("Cancelar", "", 100)
        lay.addLayout(hbox(None, ca, ok))
        ok.clicked.connect(self.guardar)
        ca.clicked.connect(self.reject)
        bq.clicked.connect(self.grid.quitar)
        self.grid.cambio.connect(self.totales)
        for w in (self.desc, self.rec):
            w.cambiado.connect(lambda *_: self.totales())
        self.pago.currentIndexChanged.connect(lambda *_: self.cuenta_pag.setEnabled(self.pago.valor() == "CRE"))
        self.cuenta_pag.setEnabled(False)
        self.con_fac.toggled.connect(lambda v: (self.nro.setEnabled(v), self.aut.setEnabled(v)))
        self.totales()

    def calcular(self):
        ls = self.grid.lineas()
        bruto = sum(l["cantidad"] * l["precio"] for l in ls)
        desc = sum(l["descuento"] for l in ls)
        total = r2(bruto - desc - self.desc.valor() + self.rec.valor())
        return ls, r2(bruto - desc), total

    def totales(self) -> None:
        _, sub, total = self.calcular()
        iva = r2(total * self.ctx.iva.iva_pct(self.fecha.fecha()) / 100) if self.con_fac.isChecked() else 0
        self.l_tot.setText(f"Subtotal: {fmt(sub)}     TOTAL Bs: {fmt(total)}     ({'IVA' if self.venta else 'Crédito fiscal'} incluido: {fmt(iva)})")
        self.l_let.setText(monto_en_letras(total) if total > 0 else "")

    def guardar(self) -> None:
        d = {"fecha": self.fecha.fecha(), "tercero_id": self.tercero.valor(), "tipo_pago": self.pago.valor(), "almacen_id": self.almacen.valor(), "con_factura": self.con_fac.isChecked(),
             "nro_factura": self.nro.text(), "nro_autorizacion": self.aut.text(), "items": self.grid.lineas(), "descuento": self.desc.valor(), "recargo": self.rec.valor(),
             "a_cuenta": self.cuenta_pag.valor(), "cuenta_pago_id": self.cuenta.valor()}
        if self.venta:
            d["vendedor_id"] = self.vend.valor()
        try:
            r = (self.ctx.ventas if self.venta else self.ctx.compras).registrar(d)
        except Exception as ex:  # noqa: BLE001
            if isinstance(ex, (ErrorNegocio, ValueError)):
                self.err.setText(str(ex))
            else:
                error(self, ex)
            return
        self.id_registrado = r["id"]
        self.accept()


class DocumentosPantalla(ListaCRUD):
    def __init__(self, ctx, venta: bool, ventana=None):
        self.venta = venta
        self.titulo = "Ventas" if venta else "Compras"
        self.subtitulo = "Notas de " + ("venta" if venta else "compra") + " con su comprobante, kardex y libro IVA generados automáticamente."
        self.desde = CampoFecha(ctx.inicio, ctx.inicio, ctx.fin)
        self.hasta = CampoFecha(ctx.fin, ctx.inicio, ctx.fin)
        cols = [Columna("numero", "Nº", 60, "int"), Columna("fecha", "Fecha", 90, "date"), Columna("tercero", "Cliente" if venta else "Proveedor", 240, estirar=True), Columna("nro_factura", "Factura", 90),
                Columna("tipo_pago", "Pago", 60), Columna("subtotal", "Subtotal", 110, "money"), Columna("total", "Total", 110, "money"), Columna("saldo", "Saldo", 110, "money"), Columna("estado_txt", "Estado", 80)]
        srv = ctx.ventas if venta else ctx.compras
        super().__init__(ctx, cols, lambda: self.datos(srv), [("Nueva " + ("venta" if venta else "compra"), self.nueva, "primario"), ("Imprimir nota", self.imprimir, ""), ("Anular", self.anular, "peligro")],
                         True, ventana, colorear=lambda f, c: tema.ROJO if f["estado"] == "A" else None, doble_clic=self.imprimir, filtros=[etiqueta("Desde"), self.desde, etiqueta("Hasta"), self.hasta])
        for w in (self.desde, self.hasta):
            w.dateChanged.connect(lambda *_: self.refrescar())
        self.botones["Nueva " + ("venta" if venta else "compra")].setEnabled(ctx.puede("COM.VENTAS" if venta else "COM.COMPRAS") and ctx.abierta)

    def datos(self, srv):
        f = srv.listar(self.desde.fecha(), self.hasta.fecha())
        for x in f:
            x["estado_txt"] = "Anulada" if x["estado"] == "A" else "Vigente"
        return f

    def nueva(self, _=None):
        DocumentoDialog(self.ctx, self.venta, self.ventana or self).exec()

    def imprimir(self, f):
        if f and self.ventana:
            self.ventana.informe("nota_venta" if self.venta else "nota_compra", {"id": f["id"]}, pedir=False)

    def anular(self, f):
        if f and confirmar(self, f"¿Anular la nota Nº {f['numero']}? Se revertirán inventario, comprobante y libro IVA.", "Anular", True):
            (self.ctx.ventas if self.venta else self.ctx.compras).anular(f["id"])


# ============================================================ cobros y pagos
class CobroDialog(QDialog):
    def __init__(self, ctx, clase: str, parent=None):
        super().__init__(parent)
        self.ctx, self.clase = ctx, clase
        self.setWindowTitle("Cobro a cliente" if clase == "CO" else "Pago a proveedor")
        self.setMinimumWidth(760)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        h = QLabel("Registrar " + ("cobro" if clase == "CO" else "pago"))
        h.setObjectName("h1")
        lay.addWidget(h)
        g = QGridLayout()
        self.fecha = CampoFecha(min(max(date.today(), ctx.inicio), ctx.fin), ctx.inicio, ctx.fin)
        self.tercero = Combo()
        self.tercero.cargar([(t["id"], t["nombre"]) for t in ctx.terceros.listar("C" if clase == "CO" else "P")], "Seleccione…")
        self.monto = CampoImporte(0.0)
        self.forma = Combo([("EFE", "Efectivo"), ("CHQ", "Cheque"), ("TRF", "Transferencia"), ("DEP", "Depósito")])
        self.cuenta = Combo()
        self.cuenta.cargar([(c["id"], f"{c['codigo']}  {c['nombre']}") for c in ctx.bancos.cuentas_banco()], None)
        self.cuenta.set_valor(ctx.cuenta_por_codigo(ctx.param("CTA_CAJA"))["id"])
        self.nro = QLineEdit()
        for i, (et, w) in enumerate([("Fecha", self.fecha), ("Cliente" if clase == "CO" else "Proveedor", self.tercero), ("Monto", self.monto), ("Forma", self.forma),
                                     ("Cuenta de caja o banco", self.cuenta), ("Nº cheque / transferencia", self.nro)]):
            g.addWidget(etiqueta(et), (i // 3) * 2, i % 3)
            g.addWidget(w, (i // 3) * 2 + 1, i % 3)
        lay.addLayout(g)
        lay.addWidget(etiqueta("Documentos pendientes (se aplican del más antiguo al más reciente)"))
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Nº", "Fecha", "Vence", "Total", "Saldo"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setMaximumHeight(190)
        lay.addWidget(self.tabla)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)
        ok, ca = boton("Registrar", "primario", 110), boton("Cancelar", "", 100)
        lay.addLayout(hbox(None, ca, ok))
        ok.clicked.connect(self.guardar)
        ca.clicked.connect(self.reject)
        self.tercero.currentIndexChanged.connect(self.cargar)

    def cargar(self) -> None:
        self.pend = self.ctx.cobros.pendientes(self.tercero.valor(), self.clase) if self.tercero.valor() else []
        self.tabla.setRowCount(len(self.pend))
        for i, p in enumerate(self.pend):
            for j, v in enumerate([p["numero"], fdate(p["fecha"]), fdate(p["vencimiento"]), fmt(p["total"]), fmt(p["saldo"])]):
                it = QTableWidgetItem(str(v))
                if j >= 3:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(i, j, it)
        if self.pend:
            self.monto.set_valor(r2(sum(p["saldo"] for p in self.pend)))

    def guardar(self) -> None:
        try:
            self.resultado = self.ctx.cobros.registrar({"clase": self.clase, "fecha": self.fecha.fecha(), "tercero_id": self.tercero.valor(), "monto": self.monto.valor(),
                                                         "forma": self.forma.valor(), "cuenta_id": self.cuenta.valor(), "nro_doc": self.nro.text()})
        except Exception as ex:  # noqa: BLE001
            if isinstance(ex, (ErrorNegocio, ValueError)):
                self.err.setText(str(ex))
            else:
                error(self, ex)
            return
        self.accept()


class CobrosPagosPantalla(ListaCRUD):
    def __init__(self, ctx, ventana=None):
        self.titulo = "Cobros y pagos"
        self.subtitulo = "Cobros a clientes y pagos a proveedores aplicados a sus documentos, con comprobante automático."
        self.clase = Combo([("CO", "Cobros a clientes"), ("PA", "Pagos a proveedores")])
        cols = [Columna("numero", "Nº", 60, "int"), Columna("fecha", "Fecha", 90, "date"), Columna("tercero", "Cliente / proveedor", 260, estirar=True), Columna("forma", "Forma", 70),
                Columna("monto", "Monto Bs", 120, "money"), Columna("estado_txt", "Estado", 80)]
        super().__init__(ctx, cols, self.datos, [("Nuevo cobro", self.nuevo_co, "primario"), ("Nuevo pago", self.nuevo_pa, ""), ("Anular", self.anular, "peligro")], True, ventana,
                         colorear=lambda f, c: tema.ROJO if f["estado"] == "A" else None, filtros=[self.clase])
        self.clase.currentIndexChanged.connect(lambda *_: self.refrescar())
        for k in ("Nuevo cobro", "Nuevo pago"):
            self.botones[k].setEnabled(ctx.puede("COM.COBROS") and ctx.abierta)

    def datos(self):
        f = self.ctx.cobros.listar(self.clase.valor())
        for x in f:
            x["estado_txt"] = "Anulado" if x["estado"] == "A" else "Vigente"
        return f

    def nuevo_co(self, _=None):
        CobroDialog(self.ctx, "CO", self.ventana or self).exec()

    def nuevo_pa(self, _=None):
        CobroDialog(self.ctx, "PA", self.ventana or self).exec()

    def anular(self, f):
        if f and confirmar(self, "¿Anular este registro? Los saldos de los documentos se restituyen.", "Anular", True):
            self.ctx.cobros.anular(f["id"])
