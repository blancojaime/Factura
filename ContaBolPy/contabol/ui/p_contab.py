"""Pantallas de contabilidad: plan de cuentas, comprobantes, tipo de cambio, conciliación bancaria y presupuesto."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QEvent, QStringListModel, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemDelegate, QAbstractItemView, QCheckBox, QCompleter, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..sistema import ErrorNegocio
from ..util import fdate, fmt, iso, parse_num, r2, to_date
from . import tema
from .base import ListaCRUD, Pantalla
from .formularios import Campo, FormDialog
from .widgets import (Banner, CampoFecha, CampoImporte, Columna, Combo, TablaDatos, aviso, boton, confirmar, error, etiqueta, hbox, info, intentar)


# =============================================================== plan de cuentas
class PlanCuentasPantalla(Pantalla):
    titulo = "Plan de cuentas"
    subtitulo = "Estructura jerárquica de cuentas (1.1.1.01.001). Las cuentas de último nivel reciben movimientos."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        c = ctx
        barra = QHBoxLayout()
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar por código o nombre…")
        self.buscar.setMaximumWidth(320)
        self.buscar.setClearButtonEnabled(True)
        barra.addWidget(self.buscar)
        barra.addStretch(1)
        self.b_nueva = boton("Nueva cuenta", "primario")
        self.b_sub = boton("Nueva subcuenta")
        self.b_edit = boton("Editar")
        self.b_del = boton("Eliminar", "peligro")
        self.b_imp = boton("Importar CSV")
        self.b_exp = boton("Exportar CSV")
        for b in (self.b_nueva, self.b_sub, self.b_edit, self.b_del, self.b_imp, self.b_exp):
            barra.addWidget(b)
        self.cuerpo.addLayout(barra)
        self.arbol = QTreeWidget()
        self.arbol.setColumnCount(6)
        self.arbol.setHeaderLabels(["Código", "Cuenta", "Tipo", "Mov.", "M.E.", "Saldo Bs"])
        self.arbol.setAlternatingRowColors(True)
        h = self.arbol.header()
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for i, w in ((0, 170), (2, 130), (3, 50), (4, 50), (5, 130)):
            self.arbol.setColumnWidth(i, w)
        self.arbol.setRootIsDecorated(True)
        self.cuerpo.addWidget(self.arbol, 1)
        self.buscar.textChanged.connect(self.filtrar)
        self.b_nueva.clicked.connect(lambda: self.editar(None))
        self.b_sub.clicked.connect(self.subcuenta)
        self.b_edit.clicked.connect(lambda: self.editar(self._sel()))
        self.arbol.itemDoubleClicked.connect(lambda *_: self.editar(self._sel()))
        self.b_del.clicked.connect(self.eliminar)
        self.b_imp.clicked.connect(self.importar)
        self.b_exp.clicked.connect(self.exportar)
        for b in (self.b_nueva, self.b_sub, self.b_edit, self.b_del, self.b_imp):
            b.setEnabled(c.puede("CONT.PLAN") and c.abierta)
        self.refrescar()

    def refrescar(self) -> None:
        c = self.ctx
        sal = c.libros.saldos_a(c.fin, incluir_cierre=True)
        self.arbol.clear()
        items: dict[int, QTreeWidgetItem] = {}
        for ct in c.db.query("SELECT * FROM cuenta ORDER BY codigo"):
            v = sal.get(ct["id"], 0.0)
            v = v if ct["naturaleza"] == "D" else -v
            it = QTreeWidgetItem([ct["codigo"], ct["nombre"], {"A": "Activo", "P": "Pasivo", "T": "Patrimonio", "I": "Ingresos", "G": "Costos y gastos", "O": "Orden"}[ct["tipo"]],
                                  "✔" if ct["es_movimiento"] else "", "$" if ct["moneda_extranjera"] else "", fmt(v) if abs(v) >= 0.005 else ""])
            it.setData(0, Qt.UserRole, ct["id"])
            it.setTextAlignment(5, Qt.AlignRight | Qt.AlignVCenter)
            it.setTextAlignment(3, Qt.AlignCenter)
            it.setTextAlignment(4, Qt.AlignCenter)
            if not ct["es_movimiento"]:
                f = it.font(0)
                f.setBold(True)
                for col in range(6):
                    it.setFont(col, f)
            if v < 0:
                it.setForeground(5, QColor(tema.ROJO))
            (items[ct["padre_id"]].addChild(it) if ct["padre_id"] in items else self.arbol.addTopLevelItem(it))
            items[ct["id"]] = it
        for i in range(self.arbol.topLevelItemCount()):
            self.arbol.topLevelItem(i).setExpanded(True)
            for j in range(self.arbol.topLevelItem(i).childCount()):
                self.arbol.topLevelItem(i).child(j).setExpanded(False)

    def filtrar(self) -> None:
        t = self.buscar.text().strip().lower()

        def visible(it: QTreeWidgetItem) -> bool:
            propio = not t or t in it.text(0).lower() or t in it.text(1).lower()
            hijos = False
            for k in range(it.childCount()):
                if visible(it.child(k)):
                    hijos = True
            it.setHidden(not (propio or hijos))
            if t and (propio or hijos):
                it.setExpanded(hijos)
            return propio or hijos
        for i in range(self.arbol.topLevelItemCount()):
            visible(self.arbol.topLevelItem(i))

    def _sel(self) -> dict | None:
        it = self.arbol.currentItem()
        return self.ctx.cuentas.obtener(it.data(0, Qt.UserRole)) if it else None

    def subcuenta(self) -> None:
        p = self._sel()
        if not p:
            aviso(self, "Seleccione la cuenta padre.")
            return
        cod = self.ctx.cuentas.siguiente_codigo(p["codigo"])
        self.editar(None, {"codigo": cod, "es_movimiento": cod.count(".") + 1 >= 5, "flujo": p["flujo"], "corriente": p["corriente"], "patr_col": p["patr_col"]})

    def editar(self, cta: dict | None, previo: dict | None = None) -> None:
        from ..services.cuentas import FLUJOS
        v = dict(cta or previo or {"es_movimiento": True, "corriente": 1, "flujo": "NA"})
        campos = [Campo("codigo", "Código", "txt", True), Campo("nombre", "Nombre de la cuenta", "txt", True, ancho=2),
                  Campo("es_movimiento", "Cuenta de movimiento (recibe asientos)", "check"), Campo("moneda_extranjera", "Maneja moneda extranjera (US$)", "check"),
                  Campo("ajustable", "Ajustable por UFV", "check"), Campo("regularizadora", "Regularizadora (naturaleza inversa)", "check"),
                  Campo("es_banco", "Cuenta bancaria", "check"), Campo("es_efectivo", "Efectivo y equivalentes (flujo de efectivo)", "check"),
                  Campo("corriente", "Corriente (corto plazo)", "check"), Campo("presupuestable", "Presupuestable", "check"),
                  Campo("flujo", "Clasificación en el flujo de efectivo", "combo", opciones=[(f, f) for f in FLUJOS], ancho=2)]
        if cta:
            v["id"] = cta["id"]

        def guardar(x):
            if cta:
                x["id"] = cta["id"]
                x["patr_col"] = cta["patr_col"]
                x["costo_tipo"] = cta["costo_tipo"]
            else:
                x["patr_col"] = (previo or {}).get("patr_col")
            self.ctx.cuentas.guardar(x)
        if FormDialog("Cuenta contable" if not cta else f"Cuenta {cta['codigo']}", campos, v, guardar, parent=self).exec():
            self.refrescar()

    def eliminar(self) -> None:
        c = self._sel()
        if c and confirmar(self, f"¿Eliminar la cuenta {c['codigo']} - {c['nombre']}?", peligro=True):
            ok, _ = intentar(self, self.ctx.cuentas.eliminar, c["id"])
            if ok:
                self.refrescar()

    def importar(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar plan de cuentas (código;nombre)", "", "CSV (*.csv *.txt)")
        if ruta:
            ok, n = intentar(self, self.ctx.cuentas.importar_csv, ruta)
            if ok:
                info(self, f"Se importaron {n} cuentas nuevas.")
                self.refrescar()

    def exportar(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar plan de cuentas", "plan_de_cuentas.csv", "CSV (*.csv)")
        if ruta:
            ok, n = intentar(self, self.ctx.cuentas.exportar_csv, ruta)
            if ok:
                info(self, f"Se exportaron {n} cuentas.")


# ================================================================= comprobantes
class SelectorCuentaDelegate(QStyledItemDelegate):
    """Edita la celda de cuenta con autocompletado por código o nombre."""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.cuentas = ctx.cuentas.listar(solo_movimiento=True)
        self.textos = [f"{c['codigo']}  {c['nombre']}" for c in self.cuentas]

    def createEditor(self, parent, option, index):
        e = QLineEdit(parent)
        comp = QCompleter(self.textos, e)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        comp.setMaxVisibleItems(12)
        e.setCompleter(comp)
        return e

    def setEditorData(self, editor, index):
        editor.setText(index.data(Qt.EditRole) or "")

    def setModelData(self, editor, model, index):
        t = editor.text().strip()
        cta = self.resolver(t)
        model.setData(index, f"{cta['codigo']}  {cta['nombre']}" if cta else t, Qt.EditRole)
        model.setData(index, cta["id"] if cta else None, Qt.UserRole)

    def resolver(self, t: str):
        if not t:
            return None
        tl = t.lower()
        for c in self.cuentas:
            if tl == f"{c['codigo']}  {c['nombre']}".lower() or tl == c["codigo"].lower():
                return c
        cod = t.split(" ")[0]
        for c in self.cuentas:
            if c["codigo"] == cod:
                return c
        cand = [c for c in self.cuentas if tl in c["nombre"].lower() or c["codigo"].startswith(tl)]
        return cand[0] if len(cand) == 1 else None


class ImporteDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        e = QLineEdit(parent)
        e.setAlignment(Qt.AlignRight)
        return e

    def setModelData(self, editor, model, index):
        v = parse_num(editor.text())
        model.setData(index, fmt(v) if v else "", Qt.EditRole)


class GridAsiento(QTableWidget):
    """Grilla de líneas con avance automático con Enter y nueva fila al llenar la última."""
    cambio = Signal()

    COL_CUENTA, COL_GLOSA, COL_DEBE, COL_HABER, COL_CENTRO = range(5)

    def __init__(self, ctx, filas: int = 8):
        super().__init__(filas, 5)
        self.ctx = ctx
        self.setHorizontalHeaderLabels(["Cuenta", "Glosa de la línea", "Debe", "Haber", "Centro de costo"])
        h = self.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for i, w in ((2, 130), (3, 130), (4, 150)):
            self.setColumnWidth(i, w)
        self.verticalHeader().setDefaultSectionSize(30)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.setItemDelegateForColumn(0, SelectorCuentaDelegate(ctx, self))
        self.setItemDelegateForColumn(2, ImporteDelegate(self))
        self.setItemDelegateForColumn(3, ImporteDelegate(self))
        self.centros = {c["id"]: c for c in ctx.db.query("SELECT * FROM centro_costo WHERE activo=1")}
        self.itemChanged.connect(self._cambio)
        self._bloq = False
        for r in range(filas):
            self._init_fila(r)

    def _init_fila(self, r: int) -> None:
        self._bloq = True
        for c in range(5):
            if not self.item(r, c):
                it = QTableWidgetItem("")
                if c in (2, 3):
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.setItem(r, c, it)
        self._bloq = False

    def agregar_fila(self) -> None:
        r = self.rowCount()
        self.insertRow(r)
        self._init_fila(r)

    def quitar_fila(self) -> None:
        r = self.currentRow()
        if r >= 0 and self.rowCount() > 2:
            self.removeRow(r)
            self.cambio.emit()

    def _cambio(self, it: QTableWidgetItem) -> None:
        if self._bloq:
            return
        r, c = it.row(), it.column()
        self._bloq = True
        if c in (2, 3) and it.text():
            otro = self.item(r, 5 - c)  # 2<->3
            if otro and otro.text():
                otro.setText("")
        if c == 0:
            cta = it.data(Qt.UserRole)
            it.setForeground(QColor(tema.ROJO if it.text() and not cta else tema.TEXTO))
            it.setToolTip("" if cta or not it.text() else "Cuenta no encontrada")
        self._bloq = False
        if r == self.rowCount() - 1 and any(self.item(r, k) and self.item(r, k).text() for k in range(4)):
            self.agregar_fila()
        self.cambio.emit()

    def closeEditor(self, editor, hint):
        super().closeEditor(editor, hint)
        if hint in (QAbstractItemDelegate.SubmitModelCache, QAbstractItemDelegate.NoHint):
            r, c = self.currentRow(), self.currentColumn()
            sig = {0: 1, 1: 2 if True else 3, 2: 3, 3: 0}.get(c)
            if c == 3:
                self.setCurrentCell(min(r + 1, self.rowCount() - 1), 0)
            elif c == 2 and not (self.item(r, 2) and self.item(r, 2).text()):
                self.setCurrentCell(r, 3)
            elif c == 2:
                self.setCurrentCell(min(r + 1, self.rowCount() - 1), 0)
            elif sig is not None:
                self.setCurrentCell(r, sig)

    def lineas(self) -> list[dict]:
        out = []
        for r in range(self.rowCount()):
            cta = self.item(r, 0).data(Qt.UserRole)
            debe, haber = parse_num(self.item(r, 2).text()), parse_num(self.item(r, 3).text())
            if not cta and not debe and not haber:
                continue
            out.append({"cuenta_id": cta, "glosa": self.item(r, 1).text().strip(), "debe": debe, "haber": haber})
        return out

    def poner_lineas(self, lineas: list[dict]) -> None:
        self._bloq = True
        self.setRowCount(max(len(lineas) + 2, 8))
        for r in range(self.rowCount()):
            self._init_fila(r)
        for r, l in enumerate(lineas):
            it = self.item(r, 0)
            it.setText(f"{l['cuenta_codigo']}  {l['cuenta_nombre']}")
            it.setData(Qt.UserRole, l["cuenta_id"])
            self.item(r, 1).setText(l.get("glosa") or "")
            self.item(r, 2).setText(fmt(l["debe"]) if l["debe"] else "")
            self.item(r, 3).setText(fmt(l["haber"]) if l["haber"] else "")
        self._bloq = False
        self.cambio.emit()


class ComprobanteDialog(QDialog):
    def __init__(self, ctx, cid: int | None, parent=None, previo: dict | None = None):
        super().__init__(parent)
        self.ctx, self.cid = ctx, cid
        self.vent = parent
        comp = ctx.vouchers.obtener(cid) if cid else None
        self.solo_lectura = bool(comp and (comp["estado"] != "V" or comp["origen"] != "MANUAL" or not ctx.puede("CONT.COMPROBANTES"))) or not ctx.abierta
        self.setWindowTitle("Comprobante contable")
        self.resize(1040, 640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        lay.setSpacing(10)
        t = QLabel("Comprobante " + (ctx.vouchers.codigo(comp) if comp else "nuevo"))
        t.setObjectName("h1")
        lay.addWidget(t)
        if comp and comp["estado"] == "A":
            a = QLabel("ESTE COMPROBANTE ESTÁ ANULADO")
            a.setStyleSheet(f"color:{tema.ROJO}; font-weight:600;")
            lay.addWidget(a)
        elif comp and comp["origen"] != "MANUAL":
            a = QLabel(f"Generado automáticamente por el módulo {comp['origen']}: solo consulta.")
            a.setObjectName("sub")
            lay.addWidget(a)
        cab = QGridLayout()
        cab.setHorizontalSpacing(14)
        self.tipo = Combo([(x["codigo"], f"{x['nombre']} ({x['codigo']})") for x in ctx.vouchers.tipos() if x["codigo"] in ("I", "E", "T", "AJ")])
        self.fecha = CampoFecha(comp["fecha"] if comp else (previo or {}).get("fecha") or min(max(date.today(), ctx.inicio), ctx.fin), ctx.inicio, ctx.fin)
        self.moneda = Combo([("BS", "Bolivianos (Bs)"), ("USD", "Dólares (US$)")])
        self.tc = CampoImporte(ctx.tc.dolar(self.fecha.fecha()), 4)
        self.glosa = QLineEdit(comp["glosa"] if comp else "")
        self.glosa.setPlaceholderText("Descripción general del comprobante")
        self.nombre = QLineEdit(comp["a_nombre"] or "" if comp else "")
        self.nombre.setPlaceholderText("Pagado a / recibido de")
        self.nro = QLineEdit(comp["nro_doc"] or "" if comp else "")
        if comp:
            self.tipo.set_valor(comp["tipo"])
            self.moneda.set_valor(comp["moneda"])
            self.tc.set_valor(comp["tc"])
        for i, (et, w, sp) in enumerate([("Tipo", self.tipo, 1), ("Fecha", self.fecha, 1), ("Moneda", self.moneda, 1), ("T.C.", self.tc, 1)]):
            cab.addWidget(etiqueta(et), 0, i)
            cab.addWidget(w, 1, i)
        cab.addWidget(etiqueta("Glosa *"), 2, 0, 1, 4)
        cab.addWidget(self.glosa, 3, 0, 1, 4)
        cab.addWidget(etiqueta("A nombre de"), 4, 0, 1, 2)
        cab.addWidget(etiqueta("Nº de documento"), 4, 2, 1, 2)
        cab.addWidget(self.nombre, 5, 0, 1, 2)
        cab.addWidget(self.nro, 5, 2, 1, 2)
        lay.addLayout(cab)
        self.grid = GridAsiento(ctx)
        lay.addWidget(self.grid, 1)
        tot = QHBoxLayout()
        self.b_add = boton("+ Línea")
        self.b_del = boton("− Quitar línea")
        tot.addWidget(self.b_add)
        tot.addWidget(self.b_del)
        tot.addStretch(1)
        self.l_debe, self.l_haber, self.l_dif = QLabel(), QLabel(), QLabel()
        for l in (self.l_debe, self.l_haber, self.l_dif):
            l.setStyleSheet("font-size:11pt; font-weight:600; padding:0 12px;")
            tot.addWidget(l)
        lay.addLayout(tot)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)
        self.b_ok = boton("Guardar comprobante", "primario", 170)
        self.b_print = boton("Imprimir")
        self.b_anular = boton("Anular", "peligro")
        self.b_close = boton("Cerrar")
        lay.addLayout(hbox(self.b_anular, self.b_print, None, self.b_close, self.b_ok))
        self.b_add.clicked.connect(self.grid.agregar_fila)
        self.b_del.clicked.connect(self.grid.quitar_fila)
        self.grid.cambio.connect(self.totales)
        self.fecha.dateChanged.connect(lambda *_: self.tc.set_valor(ctx.tc.dolar(self.fecha.fecha())))
        self.b_ok.clicked.connect(self.guardar)
        self.b_close.clicked.connect(self.reject)
        self.b_print.clicked.connect(self.imprimir)
        self.b_anular.clicked.connect(self.anular)
        if comp:
            usd = comp["moneda"] == "USD"
            self.grid.poner_lineas([{**l, "debe": l["debe_usd"] if usd else l["debe_bs"], "haber": l["haber_usd"] if usd else l["haber_bs"]} for l in comp["lineas"]])
        elif previo and previo.get("lineas"):
            self.grid.poner_lineas(previo["lineas"])
        self.b_print.setVisible(bool(comp))
        self.b_anular.setVisible(bool(comp and comp["estado"] == "V" and ctx.puede("CONT.ANULAR") and ctx.abierta))
        if self.solo_lectura:
            for w in (self.tipo, self.fecha, self.moneda, self.tc, self.glosa, self.nombre, self.nro, self.grid, self.b_add, self.b_del, self.b_ok):
                w.setEnabled(False)
        self.totales()
        (self.glosa if not comp else self.b_close).setFocus()

    def totales(self) -> None:
        ls = self.grid.lineas()
        d, h = r2(sum(l["debe"] for l in ls)), r2(sum(l["haber"] for l in ls))
        dif = r2(d - h)
        self.l_debe.setText(f"Debe: {fmt(d)}")
        self.l_haber.setText(f"Haber: {fmt(h)}")
        ok = abs(dif) < 0.005 and d > 0
        self.l_dif.setText("✔ Cuadra" if ok else f"Diferencia: {fmt(dif)}")
        self.l_dif.setStyleSheet(f"font-size:11pt; font-weight:600; padding:0 12px; color:{tema.VERDE if ok else tema.ROJO};")

    def guardar(self) -> None:
        d = {"tipo": self.tipo.valor(), "fecha": self.fecha.fecha(), "glosa": self.glosa.text(), "moneda": self.moneda.valor(), "tc": self.tc.valor(),
             "a_nombre": self.nombre.text().strip() or None, "nro_doc": self.nro.text().strip() or None, "lineas": self.grid.lineas()}
        try:
            if self.cid:
                self.ctx.vouchers.modificar(self.cid, d)
            else:
                self.cid = self.ctx.vouchers.crear(d)
        except Exception as ex:  # noqa: BLE001
            if isinstance(ex, (ErrorNegocio, ValueError)):
                self.err.setText(str(ex))
            else:
                error(self, ex)
            return
        self.accept()

    def imprimir(self) -> None:
        if self.vent and hasattr(self.vent, "informe"):
            self.vent.informe("comprobante", {"id": self.cid}, pedir=False)

    def anular(self) -> None:
        if confirmar(self, "¿Anular este comprobante? Dejará de afectar los saldos.", "Anular comprobante", True):
            ok, _ = intentar(self, self.ctx.vouchers.anular, self.cid)
            if ok:
                self.accept()


class ComprobantesPantalla(ListaCRUD):
    titulo = "Comprobantes"
    subtitulo = "Ingresos, egresos, traspasos y ajustes. Doble clic para ver o modificar."

    def __init__(self, ctx, ventana=None):
        self.desde = CampoFecha(ctx.inicio, ctx.inicio, ctx.fin)
        self.hasta = CampoFecha(ctx.fin, ctx.inicio, ctx.fin)
        self.tipo = Combo()
        self.tipo.cargar([(t["codigo"], t["nombre"]) for t in ctx.vouchers.tipos()], "Todos los tipos")
        self._v = ventana
        cols = [Columna("codigo", "Comprobante", 120), Columna("fecha", "Fecha", 95, "date"), Columna("tipo_nombre", "Tipo", 90), Columna("glosa", "Glosa", 300, estirar=True),
                Columna("a_nombre", "A nombre de", 170), Columna("debe_bs", "Debe Bs", 120, "money"), Columna("haber_bs", "Haber Bs", 120, "money"), Columna("estado_txt", "Estado", 80)]
        acc = [("Nuevo comprobante", self.nuevo, "primario"), ("Ver / Modificar", self.ver, ""), ("Anular", self.anular, "peligro"), ("Imprimir", self.imprimir, "")]
        super().__init__(ctx, cols, self.cargar_datos, acc, True, ventana, colorear=lambda f, c: tema.ROJO if f["estado"] == "A" else None, doble_clic=self.ver,
                         filtros=[etiqueta("Desde"), self.desde, etiqueta("Hasta"), self.hasta, self.tipo])
        for w in (self.desde, self.hasta):
            w.dateChanged.connect(lambda *_: self.refrescar())
        self.tipo.currentIndexChanged.connect(lambda *_: self.refrescar())
        self.botones["Nuevo comprobante"].setEnabled(ctx.puede("CONT.COMPROBANTES") and ctx.abierta)

    def cargar_datos(self):
        filas = self.ctx.vouchers.listar(self.desde.fecha(), self.hasta.fecha(), self.tipo.valor())
        for f in filas:
            f["codigo"] = self.ctx.vouchers.codigo(f)
            f["estado_txt"] = "Anulado" if f["estado"] == "A" else "Vigente"
        return filas

    def nuevo(self, _=None):
        ComprobanteDialog(self.ctx, None, self.ventana or self).exec()

    def ver(self, f):
        if f:
            ComprobanteDialog(self.ctx, f["id"], self.ventana or self).exec()

    def anular(self, f):
        if f and confirmar(self, f"¿Anular el comprobante {f['codigo']}?", "Anular", True):
            self.ctx.vouchers.anular(f["id"])

    def imprimir(self, f):
        if f and self.ventana:
            self.ventana.informe("comprobante", {"id": f["id"]}, pedir=False)


# ============================================================== tipo de cambio
class TipoCambioPantalla(ListaCRUD):
    titulo = "Tipos de cambio y UFV"
    subtitulo = "Tipo de cambio oficial del dólar y Unidad de Fomento a la Vivienda por fecha. Se usan en comprobantes, activos fijos, planillas y ajustes."

    def __init__(self, ctx, ventana=None):
        cols = [Columna("fecha", "Fecha", 120, "date"), Columna("dolar", "Dólar (Bs por US$)", 160, "num", 4), Columna("ufv", "UFV", 140, "num", 5), Columna("x", "", 10, estirar=True)]
        super().__init__(ctx, cols, lambda: sorted(ctx.tc.listar(), key=lambda r: r["fecha"], reverse=True),
                         [("Agregar / modificar", self.editar, "primario"), ("Eliminar", self.eliminar, "peligro")], False, ventana, doble_clic=self.editar)

    def editar(self, f):
        v = f or {"fecha": min(max(date.today(), self.ctx.inicio), self.ctx.fin), "dolar": self.ctx.tc.dolar(), "ufv": self.ctx.tc.ufv()}
        campos = [Campo("fecha", "Fecha", "date", True), Campo("dolar", "Dólar (Bs)", "num", True, decimales=4), Campo("ufv", "UFV", "num", decimales=5)]
        FormDialog("Tipo de cambio", campos, v, lambda x: self.ctx.tc.guardar(x["fecha"], x["dolar"], x["ufv"]), "El tipo de cambio rige desde esa fecha hasta la siguiente cargada.", self.ventana or self).exec()

    def eliminar(self, f):
        if f and confirmar(self, f"¿Eliminar el registro del {fdate(f['fecha'])}?", peligro=True):
            self.ctx.tc.eliminar(f["fecha"])


# ================================================================== conciliación
class ConciliacionPantalla(Pantalla):
    titulo = "Conciliación bancaria"
    subtitulo = "Marque los movimientos que figuran en el extracto del banco. Los no marcados quedan como depósitos en tránsito o cheques en circulación."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        top = QHBoxLayout()
        self.cuenta = Combo()
        self.cuenta.cargar([(c["id"], f"{c['codigo']}  {c['nombre']}") for c in ctx.bancos.cuentas_banco()], None)
        self.fecha = CampoFecha(ctx.fin, ctx.inicio, ctx.fin)
        self.extracto = CampoImporte(0.0)
        for et, w in (("Cuenta", self.cuenta), ("Al", self.fecha), ("Saldo según extracto", self.extracto)):
            top.addWidget(etiqueta(et))
            top.addWidget(w)
        top.addStretch(1)
        self.b_conc = boton("Conciliar marcados", "primario")
        self.b_rep = boton("Informe")
        top.addWidget(self.b_conc)
        top.addWidget(self.b_rep)
        self.cuerpo.addLayout(top)
        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(["", "Fecha", "Comprobante", "Detalle", "Depósitos", "Cheques / cargos"])
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        for i, w in ((0, 40), (1, 100), (2, 120), (4, 120), (5, 130)):
            self.tabla.setColumnWidth(i, w)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        self.cuerpo.addWidget(self.tabla, 1)
        self.resumen = QLabel("")
        self.resumen.setStyleSheet("font-size:10.5pt;")
        self.cuerpo.addWidget(self.resumen)
        self.pend: list[dict] = []
        self.cuenta.currentIndexChanged.connect(lambda *_: self.refrescar())
        self.fecha.dateChanged.connect(lambda *_: self.refrescar())
        self.extracto.cambiado.connect(lambda *_: self.refrescar())
        self.b_conc.clicked.connect(self.conciliar)
        self.b_rep.clicked.connect(lambda: self.ventana.informe("conciliacion", {"cuenta": self.cuenta.valor(), "fecha": self.fecha.fecha(), "saldo_extracto": self.extracto.valor()}, pedir=False) if self.cuenta.valor() else None)
        self.refrescar()

    def refrescar(self) -> None:
        cid = self.cuenta.valor()
        self.tabla.setRowCount(0)
        if not cid:
            self.resumen.setText("Seleccione una cuenta de banco o caja.")
            return
        r = self.ctx.bancos.conciliacion(cid, self.fecha.fecha(), self.extracto.valor() if self.extracto.valor() else None)
        self.pend = r["pendientes"]
        self.tabla.setRowCount(len(self.pend))
        for i, p in enumerate(self.pend):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked)
            self.tabla.setItem(i, 0, chk)
            vals = [fdate(p["fecha"]), f"{p['tipo']}-{p['numero']}", p["glosa"], fmt(p["debe"]) if p["debe"] else "", fmt(p["haber"]) if p["haber"] else ""]
            for j, v in enumerate(vals, 1):
                it = QTableWidgetItem(v)
                if j >= 4:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(i, j, it)
        txt = (f"Saldo según libros: <b>{fmt(r['saldo_libros'])}</b>   ·   Depósitos en tránsito: <b>{fmt(r['depositos_transito'])}</b>   ·   "
               f"Cheques en circulación: <b>{fmt(r['cheques_circulacion'])}</b>   ·   Saldo bancario calculado: <b>{fmt(r['saldo_banco_calculado'])}</b>")
        if r["diferencia"] is not None:
            col = tema.VERDE if abs(r["diferencia"]) < 0.005 else tema.ROJO
            txt += f"   ·   <span style='color:{col}'>Diferencia con extracto: <b>{fmt(r['diferencia'])}</b></span>"
        self.resumen.setText(txt)

    def conciliar(self) -> None:
        ids = [self.pend[i]["id"] for i in range(self.tabla.rowCount()) if self.tabla.item(i, 0).checkState() == Qt.Checked]
        if not ids:
            aviso(self, "Marque los movimientos que figuran en el extracto bancario.")
            return
        ok, _ = intentar(self, self.ctx.bancos.conciliar, ids, self.fecha.fecha())
        if ok:
            self.refrescar()


# ================================================================== presupuesto
class PresupuestoPantalla(Pantalla):
    titulo = "Presupuesto"
    subtitulo = "Presupuesto mensual por cuenta de gasto. Si activa el control en Parámetros, no se permiten comprobantes que excedan lo presupuestado."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        top = QHBoxLayout()
        self.cuenta = Combo()
        self.cuenta.cargar([(c["id"], f"{c['codigo']}  {c['nombre']}") for c in ctx.cuentas.listar(solo_movimiento=True) if c["tipo"] == "G"], None)
        top.addWidget(etiqueta("Cuenta"))
        top.addWidget(self.cuenta, 1)
        self.b_rep = boton("Repetir enero en todos")
        self.b_save = boton("Guardar presupuesto", "primario")
        top.addWidget(self.b_rep)
        top.addWidget(self.b_save)
        self.cuerpo.addLayout(top)
        g = QGridLayout()
        g.setSpacing(8)
        self.campos: list[CampoImporte] = []
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        for i, m in enumerate(meses):
            g.addWidget(etiqueta(m), (i // 4) * 2, i % 4)
            c = CampoImporte(0.0)
            self.campos.append(c)
            g.addWidget(c, (i // 4) * 2 + 1, i % 4)
        cont = QFrame()
        cont.setObjectName("panel")
        cont.setLayout(g)
        g.setContentsMargins(16, 12, 16, 12)
        self.cuerpo.addWidget(cont)
        self.cuerpo.addWidget(etiqueta("Ejecución presupuestaria", "h1"))
        self.tabla = TablaDatos([Columna("cuenta", "Cuenta", 300, estirar=True), Columna("presupuesto", "Presupuesto", 130, "money"), Columna("ejecutado", "Ejecutado", 130, "money"),
                                 Columna("saldo", "Saldo", 130, "money"), Columna("pct", "% ejecución", 100, "pct")])
        self.cuerpo.addWidget(self.tabla, 1)
        self.cuenta.currentIndexChanged.connect(self.cargar_cuenta)
        self.b_rep.clicked.connect(lambda: [c.set_valor(self.campos[0].valor()) for c in self.campos])
        self.b_save.clicked.connect(self.guardar)
        self.b_save.setEnabled(ctx.puede("CONT.PRESUPUESTO"))
        self.cargar_cuenta()
        self.refrescar()

    def cargar_cuenta(self) -> None:
        if self.cuenta.valor():
            for c, v in zip(self.campos, self.ctx.presupuesto.obtener(self.cuenta.valor())):
                c.set_valor(v)

    def guardar(self) -> None:
        if not self.cuenta.valor():
            return
        ok, _ = intentar(self, self.ctx.presupuesto.guardar, self.cuenta.valor(), [c.valor() for c in self.campos])
        if ok:
            self.refrescar()

    def refrescar(self) -> None:
        self.tabla.cargar([{**r, "cuenta": f"{r['codigo']} {r['nombre']}"} for r in self.ctx.presupuesto.ejecucion()])
