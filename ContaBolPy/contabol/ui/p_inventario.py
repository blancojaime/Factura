"""Pantallas de inventarios: ítems, catálogos auxiliares y movimientos."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemDelegate, QAbstractItemView, QDialog, QGridLayout, QHeaderView, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout)

from ..sistema import ErrorNegocio
from ..util import fmt, parse_num, to_date
from . import tema
from .base import ListaCRUD
from .formularios import Campo, FormDialog
from .p_comercial import ItemDelegate
from .p_contab import ImporteDelegate
from .widgets import CampoFecha, Columna, Combo, boton, confirmar, error, etiqueta, hbox, info


class ItemsPantalla(ListaCRUD):
    titulo = "Ítems y precios"
    subtitulo = "Catálogo de productos y servicios. El costo promedio y el stock se actualizan con cada movimiento."

    def __init__(self, ctx, ventana=None):
        cols = [Columna("codigo", "Código", 100), Columna("nombre", "Descripción", 280, estirar=True), Columna("grupo", "Grupo", 130), Columna("unidad", "Unidad", 70),
                Columna("precio_venta", "Precio venta", 110, "money"), Columna("costo_prom", "Costo promedio", 120, "num", 4), Columna("stock", "Stock", 100, "num"),
                Columna("stock_min", "Mínimo", 80, "num"), Columna("activo", "Activo", 60, "bool")]
        super().__init__(ctx, cols, lambda: ctx.inventario.items(solo_activos=False), [("Nuevo ítem", self.editar, "primario"), ("Modificar", self.editar, ""),
                                                                                       ("Kardex", self.kardex, ""), ("Eliminar", self.eliminar, "peligro")], True, ventana, doble_clic=self.editar,
                         colorear=lambda f, c: tema.ROJO if (c.clave == "stock" and f["stock_min"] > 0 and f["stock"] < f["stock_min"]) else None)

    def editar(self, f=None):
        nuevo = not f or "id" not in f
        v = dict(f) if not nuevo else {"activo": 1, "tipo": "M"}
        campos = [Campo("codigo", "Código", "txt", True), Campo("nombre", "Descripción", "txt", True, ancho=2),
                  Campo("grupo_id", "Grupo", "combo", opciones=[(g["id"], g["nombre"]) for g in self.ctx.inventario.catalogo("grupo_item")], vacio="(sin grupo)"),
                  Campo("unidad_id", "Unidad de medida", "combo", opciones=[(u["id"], f"{u['codigo']} - {u['nombre']}") for u in self.ctx.inventario.catalogo("unidad")], vacio="(sin unidad)"),
                  Campo("precio_venta", "Precio de venta (Bs, con IVA)", "money"), Campo("stock_min", "Stock mínimo", "num"),
                  Campo("es_servicio", "Es un servicio (no controla stock)", "check"), Campo("controla_venc", "Controla lotes y vencimientos", "check"), Campo("activo", "Activo", "check")]

        def guardar(x):
            x["id"] = None if nuevo else f["id"]
            self.ctx.inventario.guardar_item(x)
        FormDialog("Ítem", campos, v, guardar, parent=self.ventana or self).exec()

    def eliminar(self, f):
        if f and confirmar(self, f"¿Eliminar el ítem {f['codigo']}?", peligro=True):
            self.ctx.inventario.eliminar_item(f["id"])

    def kardex(self, f):
        if f and self.ventana:
            self.ventana.informe("kardex_item", {"item": f["id"], "desde": self.ctx.inicio, "hasta": self.ctx.fin}, pedir=False)


class CatalogoPantalla(ListaCRUD):
    """Almacenes, unidades de medida, grupos de ítems y vendedores."""
    DEF = {"almacen": ("Almacenes", "Depósitos donde se guarda la mercadería.", True), "unidad": ("Unidades de medida", "Kilos, litros, cajas, docenas…", False),
           "grupo_item": ("Grupos de ítems", "Clasificación de productos.", False), "vendedor": ("Vendedores", "Vendedores y su porcentaje de comisión.", False)}

    def __init__(self, ctx, tabla: str, ventana=None):
        self.tabla_db = tabla
        self.titulo, self.subtitulo, _ = self.DEF[tabla]
        cols = [Columna("codigo", "Código", 100), Columna("nombre", "Nombre", 300, estirar=True)]
        if tabla == "almacen":
            cols.append(Columna("direccion", "Dirección", 260))
        if tabla == "vendedor":
            cols.append(Columna("comision", "Comisión %", 100, "pct"))
        super().__init__(ctx, cols, lambda: ctx.inventario.catalogo(tabla), [("Nuevo", self.editar, "primario"), ("Modificar", self.editar, ""), ("Eliminar", self.eliminar, "peligro")],
                         True, ventana, doble_clic=self.editar)

    def editar(self, f=None):
        nuevo = not f or "id" not in f
        campos = [Campo("codigo", "Código", "txt", True, maximo=12), Campo("nombre", "Nombre", "txt", True, ancho=2)]
        if self.tabla_db == "almacen":
            campos.append(Campo("direccion", "Dirección", ancho=2))
        if self.tabla_db == "vendedor":
            campos.append(Campo("comision", "Comisión (%)", "num"))

        def guardar(x):
            x["id"] = None if nuevo else f["id"]
            self.ctx.inventario.guardar_catalogo(self.tabla_db, x)
        FormDialog(self.titulo, campos, None if nuevo else f, guardar, parent=self.ventana or self, ancho=560).exec()

    def eliminar(self, f):
        if f and confirmar(self, f"¿Eliminar {f['nombre']}?", peligro=True):
            self.ctx.inventario.eliminar_catalogo(self.tabla_db, f["id"])


class FechaDelegate(__import__("PySide6.QtWidgets", fromlist=["QStyledItemDelegate"]).QStyledItemDelegate):
    pass


class MovimientoDialog(QDialog):
    TIPOS = [("INI", "Stock inicial"), ("ING", "Ingreso por compra/otros"), ("SAL", "Salida"), ("AJE", "Ajuste de entrada (sobrante)"), ("AJS", "Ajuste de salida (merma, faltante)"), ("TRA", "Traspaso entre almacenes")]

    def __init__(self, ctx, parent=None, tipo: str = "INI"):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Movimiento de inventario")
        self.resize(920, 600)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        h = QLabel("Movimiento de inventario")
        h.setObjectName("h1")
        lay.addWidget(h)
        g = QGridLayout()
        self.tipo = Combo(self.TIPOS)
        self.tipo.set_valor(tipo)
        self.fecha = CampoFecha(min(max(date.today(), ctx.inicio), ctx.fin), ctx.inicio, ctx.fin)
        alms = [(a["id"], a["nombre"]) for a in ctx.inventario.catalogo("almacen")]
        self.alm = Combo(alms)
        self.dest = Combo(alms)
        self.glosa = QLineEdit()
        self.asiento = Combo([(True, "Sí, generar comprobante"), (False, "No generar comprobante")])
        for i, (et, w) in enumerate([("Tipo de movimiento", self.tipo), ("Fecha", self.fecha), ("Almacén (origen)", self.alm), ("Almacén destino (traspasos)", self.dest)]):
            g.addWidget(etiqueta(et), 0, i)
            g.addWidget(w, 1, i)
        g.addWidget(etiqueta("Glosa"), 2, 0, 1, 3)
        g.addWidget(etiqueta("Contabilizar"), 2, 3)
        g.addWidget(self.glosa, 3, 0, 1, 3)
        g.addWidget(self.asiento, 3, 3)
        lay.addLayout(g)
        self.tabla = QTableWidget(8, 5)
        self.tabla.setHorizontalHeaderLabels(["Ítem", "Cantidad", "Costo unitario", "Lote", "Vence (dd/mm/aaaa)"])
        h_ = self.tabla.horizontalHeader()
        h_.setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in ((1, 100), (2, 120), (3, 100), (4, 150)):
            self.tabla.setColumnWidth(i, w)
        self.tabla.setAlternatingRowColors(True)
        self.deleg = ItemDelegate([i for i in ctx.inventario.items() if not i["es_servicio"]])
        self.tabla.setItemDelegateForColumn(0, self.deleg)
        self.tabla.setItemDelegateForColumn(1, ImporteDelegate(self.tabla))
        self.tabla.setItemDelegateForColumn(2, ImporteDelegate(self.tabla))
        for r in range(8):
            for c in range(5):
                self.tabla.setItem(r, c, QTableWidgetItem(""))
        self.tabla.itemChanged.connect(self._cambio)
        lay.addWidget(self.tabla, 1)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)
        ok, ca = boton("Registrar movimiento", "primario", 170), boton("Cancelar", "", 100)
        lay.addLayout(hbox(None, ca, ok))
        ok.clicked.connect(self.guardar)
        ca.clicked.connect(self.reject)
        self.tipo.currentIndexChanged.connect(self._tipo)
        self._tipo()

    def _tipo(self) -> None:
        t = self.tipo.valor()
        self.dest.setEnabled(t == "TRA")
        self.tabla.setColumnHidden(2, t in ("SAL", "AJS", "TRA"))

    def _cambio(self, it) -> None:
        if it.column() == 0 and it.data(Qt.UserRole) and not self.tabla.item(it.row(), 2).text() and self.tipo.valor() in ("ING", "AJE"):
            self.tabla.blockSignals(True)
            self.tabla.item(it.row(), 2).setText(fmt(self.ctx.inventario.item(it.data(Qt.UserRole))["costo_prom"], 4))
            self.tabla.blockSignals(False)
        if it.row() == self.tabla.rowCount() - 1 and it.text():
            self.tabla.blockSignals(True)
            r = self.tabla.rowCount()
            self.tabla.insertRow(r)
            for c in range(5):
                self.tabla.setItem(r, c, QTableWidgetItem(""))
            self.tabla.blockSignals(False)

    def guardar(self) -> None:
        items = []
        for r in range(self.tabla.rowCount()):
            idx = self.tabla.item(r, 0).data(Qt.UserRole)
            if not idx:
                continue
            ct = self.tabla.item(r, 2).text()
            items.append({"item_id": idx, "cantidad": parse_num(self.tabla.item(r, 1).text()), "costo_unit": parse_num(ct) if ct else None,
                          "lote": self.tabla.item(r, 3).text().strip() or None, "vencimiento": to_date(self.tabla.item(r, 4).text())})
        try:
            self.ctx.inventario.registrar({"tipo": self.tipo.valor(), "fecha": self.fecha.fecha(), "almacen_id": self.alm.valor(), "almacen_dest_id": self.dest.valor() if self.tipo.valor() == "TRA" else None,
                                           "glosa": self.glosa.text() or dict(self.TIPOS)[self.tipo.valor()], "items": items, "generar_asiento": bool(self.asiento.valor())})
        except Exception as ex:  # noqa: BLE001
            if isinstance(ex, (ErrorNegocio, ValueError)):
                self.err.setText(str(ex))
            else:
                error(self, ex)
            return
        self.accept()


class MovimientosPantalla(ListaCRUD):
    titulo = "Movimientos de inventario"
    subtitulo = "Stock inicial, ajustes y traspasos. Las compras y ventas generan sus movimientos automáticamente."

    def __init__(self, ctx, ventana=None):
        cols = [Columna("numero", "Nº", 60, "int"), Columna("fecha", "Fecha", 90, "date"), Columna("tipo", "Tipo", 60), Columna("almacen", "Almacén", 160), Columna("glosa", "Glosa", 300, estirar=True),
                Columna("total", "Valor Bs", 120, "money"), Columna("estado_txt", "Estado", 80)]
        super().__init__(ctx, cols, self.datos, [("Nuevo movimiento", self.nuevo, "primario"), ("Anular", self.anular, "peligro")], True, ventana,
                         colorear=lambda f, c: tema.ROJO if f["estado"] == "A" else None)
        self.botones["Nuevo movimiento"].setEnabled(ctx.puede("INV.MOVIMIENTOS") and ctx.abierta)

    def datos(self):
        f = self.ctx.inventario.movimientos()
        for x in f:
            x["estado_txt"] = "Anulado" if x["estado"] == "A" else "Vigente"
        return f

    def nuevo(self, _=None):
        MovimientoDialog(self.ctx, self.ventana or self).exec()

    def anular(self, f):
        if f and confirmar(self, "¿Anular el movimiento y revertir existencias?", "Anular", True):
            self.ctx.inventario.anular(f["id"])
