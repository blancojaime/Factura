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
        self.arbol.setColumnCount(8)
        self.arbol.setHeaderLabels(["Código", "Cuenta", "Tipo", "Mov.", "Presup.", "Ajust.", "M.E.", "Saldo Bs"])
        self.arbol.setAlternatingRowColors(False)
        self.arbol.setStyleSheet("QTreeWidget::item { padding: 4px 2px; }")
        h = self.arbol.header()
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for i, w in ((0, 180), (2, 130), (3, 55), (4, 65), (5, 60), (6, 50), (7, 140)):
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

    COLORES = {"A": ("#1F4E8C", "#DDE9F7"), "P": ("#A8322D", "#F8E1DF"), "T": ("#2E7D4F", "#E0F1E7"), "I": ("#0F7C8A", "#DAF0F3"), "G": ("#B7791F", "#FBEFD5"), "O": ("#5B6675", "#E8EBEF")}

    def refrescar(self) -> None:
        from PySide6.QtGui import QBrush
        c = self.ctx
        sal = c.libros.saldos_a(c.fin, incluir_cierre=True)
        self.arbol.clear()
        items: dict[int, QTreeWidgetItem] = {}
        for ct in c.db.query("SELECT * FROM cuenta ORDER BY codigo"):
            v = sal.get(ct["id"], 0.0)
            v = v if ct["naturaleza"] == "D" else -v
            fuerte, claro = self.COLORES[ct["tipo"]]
            it = QTreeWidgetItem([ct["codigo"], ct["nombre"], {"A": "Activo", "P": "Pasivo", "T": "Patrimonio", "I": "Ingresos", "G": "Costos y gastos", "O": "Orden"}[ct["tipo"]],
                                  "✔" if ct["es_movimiento"] else "", "✔" if ct["presupuestable"] else "", "✔" if ct["ajustable"] else "", "$" if ct["moneda_extranjera"] else "",
                                  fmt(v) if abs(v) >= 0.005 else ""])
            it.setData(0, Qt.UserRole, ct["id"])
            for col in (3, 4, 5, 6):
                it.setTextAlignment(col, Qt.AlignCenter)
            it.setTextAlignment(7, Qt.AlignRight | Qt.AlignVCenter)
            nivel = ct["nivel"]
            for col in range(8):
                f = it.font(col)
                f.setBold(not ct["es_movimiento"])
                it.setFont(col, f)
                if nivel == 1:
                    it.setBackground(col, QBrush(QColor(fuerte)))
                    it.setForeground(col, QBrush(QColor("white")))
                elif nivel == 2:
                    it.setBackground(col, QBrush(QColor(claro)))
                    it.setForeground(col, QBrush(QColor(fuerte)))
                elif nivel in (3, 4):
                    it.setBackground(col, QBrush(QColor(claro).lighter(112)))
                    it.setForeground(col, QBrush(QColor(fuerte)))
                else:
                    it.setForeground(col, QBrush(QColor(tema.TEXTO)))
            if ct["es_movimiento"]:
                it.setForeground(0, QBrush(QColor(fuerte)))
                if v < 0:
                    it.setForeground(7, QBrush(QColor(tema.ROJO)))
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
class ImporteDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        e = QLineEdit(parent)
        e.setAlignment(Qt.AlignRight)
        return e

    def setModelData(self, editor, model, index):
        v = parse_num(editor.text())
        model.setData(index, fmt(v) if v else "", Qt.EditRole)


from .p_comprobante import ComprobanteDialog  # noqa: E402


class ComprobantesPantalla(Pantalla):
    """Control de comprobantes: todos los comprobantes con su información, detalle del seleccionado y acciones (nuevo, copiar, eliminar, revertir, anular, imprimir, Excel y Word)."""
    titulo = "Control de comprobantes"
    subtitulo = "Consulte todos los comprobantes; seleccione uno para ver su detalle, copiarlo, revertirlo, eliminarlo o imprimirlo."

    ORDENES = [("fecha", "Fecha"), ("numero", "Número"), ("tipo", "Tipo y número"), ("importe", "Importe"), ("beneficiario", "Beneficiario")]

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        from PySide6.QtWidgets import QGridLayout, QLabel, QLineEdit, QPlainTextEdit
        self.desde = CampoFecha(ctx.inicio, ctx.inicio, ctx.fin)
        self.hasta = CampoFecha(ctx.fin, ctx.inicio, ctx.fin)
        self.tipo = Combo()
        self.tipo.cargar([(t["codigo"], t["nombre"]) for t in ctx.vouchers.tipos()], "Todos")
        self.estado = Combo([("", "Todos"), ("V", "Vigentes"), ("A", "Anulados")])
        self.orden = Combo(self.ORDENES)
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar en glosa, beneficiario o Nº de documento…")
        self.buscar.setClearButtonEnabled(True)
        barra = QHBoxLayout()
        for et, w in (("Desde", self.desde), ("Hasta", self.hasta), ("Tipo", self.tipo), ("Estado", self.estado), ("Ordenar por", self.orden)):
            barra.addWidget(etiqueta(et))
            barra.addWidget(w)
        barra.addWidget(self.buscar, 1)
        self.cuerpo.addLayout(barra)
        cols = [Columna("codigo", "Cbte.", 105), Columna("fecha", "Fecha", 90, "date"), Columna("tipo_nombre", "Tipo", 85), Columna("origen_txt", "Origen", 85),
                Columna("a_nombre", "Beneficiario / a nombre de", 220, estirar=True), Columna("nro_doc", "Nº doc.", 90), Columna("glosa", "Glosa", 260),
                Columna("debe_bs", "Total debe Bs", 115, "money"), Columna("haber_bs", "Total haber Bs", 115, "money"), Columna("estado_txt", "Estado", 75), Columna("usuario", "Usuario", 75)]
        self.tabla = TablaDatos(cols)
        self.cuerpo.addWidget(self.tabla, 3)
        self.l_total = QLabel("")
        self.cuerpo.addWidget(self.l_total)
        # ---- panel inferior: detalle + acciones
        panel = QFrame()
        panel.setObjectName("banner")
        pl = QHBoxLayout(panel)
        pl.setContentsMargins(14, 10, 14, 10)
        det = QGridLayout()
        det.setHorizontalSpacing(10)
        det.setVerticalSpacing(5)
        self.d = {}
        campos = [("cbte", "Cbte.", 0, 0), ("fecha", "Fecha", 0, 1), ("tc", "Dólar", 0, 2), ("ufv", "U.F.V.", 0, 3), ("estado", "Estado", 1, 0), ("origen", "Origen", 1, 1),
                  ("banco", "Banco / Cheque", 1, 2), ("usuario", "Usuario", 1, 3), ("nombre", "A nombre de", 2, 0), ("doc", "Doc. resp.", 2, 2), ("factura", "Factura vinculada", 3, 0)]
        for k, et, r, c in campos:
            lab = QLabel(et + ":")
            lab.setObjectName("etq")
            val = QLineEdit()
            val.setReadOnly(True)
            self.d[k] = val
            det.addWidget(lab, r, c * 2)
            det.addWidget(val, r, c * 2 + 1, 1, 3 if (r, c) in ((2, 0), (3, 0)) else 1)
        self.d["glosa"] = QPlainTextEdit()
        self.d["glosa"].setReadOnly(True)
        self.d["glosa"].setMaximumHeight(52)
        lg = QLabel("Glosa:")
        lg.setObjectName("etq")
        det.addWidget(lg, 4, 0)
        det.addWidget(self.d["glosa"], 4, 1, 1, 7)
        self.t_lin = TablaDatos([Columna("cuenta_codigo", "Cuenta", 110), Columna("cuenta_nombre", "Nombre de la cuenta", 240, estirar=True), Columna("glosa", "Glosa de línea", 160),
                                 Columna("debe_bs", "Debe Bs", 100, "money"), Columna("haber_bs", "Haber Bs", 100, "money")])
        self.t_lin.setMaximumHeight(130)
        izq = QVBoxLayout()
        izq.addLayout(det)
        izq.addWidget(self.t_lin)
        pl.addLayout(izq, 1)
        acc = QGridLayout()
        acc.setSpacing(6)
        defs = [("Nuevo", self.nuevo, "primario"), ("Copiar", self.copiar, ""), ("Eliminar", self.eliminar, "peligro"), ("Revertir", self.revertir, ""), ("Anular", self.anular, "peligro"),
                ("Ver / Modificar", self.ver, ""), ("Imprimir", self.imprimir, ""), ("Enviar a Excel", self.a_excel, "exito"), ("Enviar a Word", self.a_word, ""), ("Actualizar", self.refrescar, ""),
                ("Salir", self.salir, "")]
        self.botones = {}
        for i, (t, fn, tipo) in enumerate(defs):
            b = boton(t, tipo, 120)
            b.clicked.connect(lambda _=False, f=fn: f())
            acc.addWidget(b, i // 2, i % 2)
            self.botones[t] = b
        pl.addLayout(acc)
        self.cuerpo.addWidget(panel, 2)
        self.tabla.seleccion.connect(self.mostrar)
        self.tabla.doble_clic.connect(lambda f: self.ver())
        for w in (self.desde, self.hasta):
            w.dateChanged.connect(lambda *_: self.refrescar())
        for w in (self.tipo, self.estado, self.orden):
            w.currentIndexChanged.connect(lambda *_: self.refrescar())
        self.buscar.textChanged.connect(lambda *_: self.refrescar())
        puede = ctx.puede("CONT.COMPROBANTES") and ctx.abierta
        for k in ("Nuevo", "Copiar", "Revertir"):
            self.botones[k].setEnabled(puede)
        for k in ("Eliminar", "Anular"):
            self.botones[k].setEnabled(ctx.puede("CONT.ANULAR") and ctx.abierta)
        self.refrescar()

    # ------------------------------------------------------------------ datos
    def _filtros(self) -> dict:
        return {"desde": self.desde.fecha(), "hasta": self.hasta.fecha(), "tipo": self.tipo.valor(), "estado": self.estado.valor() or ""}

    def refrescar(self, *_):
        v = self.ctx.vouchers
        filas = v.listar(self.desde.fecha(), self.hasta.fecha(), self.tipo.valor(), self.buscar.text().strip(), self.estado.valor() or None)
        usuarios = {u["id"]: u["login"] for u in self.ctx.sistema.listar_usuarios()}
        for f in filas:
            f["codigo"] = v.codigo(f)
            f["estado_txt"] = "Anulado" if f["estado"] == "A" else "Vigente"
            f["origen_txt"] = f["origen"].title()
            f["usuario"] = usuarios.get(f["creado_por"], "")
        clave = {"fecha": lambda f: (f["fecha"], f["tipo"], f["numero"]), "numero": lambda f: (f["numero"], f["fecha"]), "tipo": lambda f: (f["tipo"], f["mes"], f["numero"]),
                 "importe": lambda f: -f["debe_bs"], "beneficiario": lambda f: (f["a_nombre"] or "~").lower()}[self.orden.valor() or "fecha"]
        filas.sort(key=clave)
        sel = self.tabla.fila_actual()
        self.tabla.cargar(filas, lambda f, c: tema.ROJO if f["estado"] == "A" else None)
        vig = [f for f in filas if f["estado"] != "A"]
        self.l_total.setText(f"{len(filas)} comprobantes ({len(filas) - len(vig)} anulados) · Total debe Bs {fmt(sum(f['debe_bs'] for f in vig))} · Total haber Bs {fmt(sum(f['haber_bs'] for f in vig))}")
        if filas:
            i = next((k for k, f in enumerate(filas) if sel and f["id"] == sel["id"]), len(filas) - 1 if self.orden.valor() in (None, "fecha", "numero", "tipo") else 0)
            self.tabla.selectRow(i)
        else:
            self.mostrar(None)

    def mostrar(self, f):
        for k, w in self.d.items():
            (w.setPlainText if k == "glosa" else w.setText)("")
        self.t_lin.cargar([])
        if not f:
            return
        c = self.ctx.vouchers.obtener(f["id"])
        d = self.d
        d["cbte"].setText(f["codigo"])
        d["fecha"].setText(fdate(c["fecha"]))
        d["tc"].setText(f"{c['tc']:.4f}" if c["moneda"] == "USD" else f"{self.ctx.tc.dolar(c['fecha']):.4f}")
        d["ufv"].setText(f"{(c['ufv'] or self.ctx.tc.ufv(c['fecha'])):.5f}")
        d["estado"].setText("Anulado" if c["estado"] == "A" else "Vigente")
        d["origen"].setText(c["origen"].title() + (f" (ref. {c['ref_id']})" if c["ref_id"] else ""))
        banco = self.ctx.cuentas.obtener(c["banco_id"])["nombre"] if c["banco_id"] else ""
        d["banco"].setText((banco + (f" · Cheque {c['nro_cheque']}" if c["nro_cheque"] else "")) or "—")
        d["usuario"].setText(f.get("usuario", ""))
        d["nombre"].setText(c["a_nombre"] or "")
        d["doc"].setText(c["nro_doc"] or "")
        fv = self.ctx.vouchers.factura_vinculada(c["id"])
        rev = self.ctx.vouchers.reversion_de(c["id"])
        d["factura"].setText((f"Nº {fv['nro_factura']} · {fv['razon_social']} · IVA Bs {fmt(fv['iva'])} ({'Compras' if fv['libro'] == 'C' else 'Ventas'})" if fv else "Sin factura vinculada")
                             + (f"   |   Revertido por el comprobante {self.ctx.vouchers.codigo(rev)}" if rev else ""))
        d["glosa"].setPlainText(c["glosa"])
        self.t_lin.cargar(c["lineas"])

    # ---------------------------------------------------------------- acciones
    def _sel(self):
        f = self.tabla.fila_actual()
        if not f:
            aviso(self, "Seleccione un comprobante de la tabla.")
        return f

    def nuevo(self):
        ComprobanteDialog(self.ctx, None, self.ventana or self).exec()
        self.refrescar()

    def copiar(self):
        f = self._sel()
        if f:
            c = self.ctx.vouchers.obtener(f["id"])
            previo = {"tipo": c["tipo"], "glosa": c["glosa"], "a_nombre": c["a_nombre"], "nro_doc": c["nro_doc"],
                      "lineas": [{"cuenta_id": l["cuenta_id"], "debe": l["debe_bs"], "haber": l["haber_bs"], "glosa": l["glosa"]} for l in c["lineas"]]}
            ComprobanteDialog(self.ctx, None, self.ventana or self, previo=previo).exec()
            self.refrescar()

    def ver(self):
        f = self.tabla.fila_actual()
        if f:
            ComprobanteDialog(self.ctx, f["id"], self.ventana or self).exec()
            self.refrescar()

    def eliminar(self):
        f = self._sel()
        if f and confirmar(self, f"¿Eliminar definitivamente el comprobante {f['codigo']}?\nSolo es posible si es el último de su tipo y mes; si no, use Anular o Revertir.", "Eliminar", True):
            if intentar(self, self.ctx.vouchers.eliminar, f["id"])[0]:
                self.refrescar()

    def anular(self):
        f = self._sel()
        if f and confirmar(self, f"¿Anular el comprobante {f['codigo']}?\nQuedará en los libros como anulado, sin efecto contable.", "Anular", True):
            if intentar(self, self.ctx.vouchers.anular, f["id"])[0]:
                self.refrescar()

    def revertir(self):
        f = self._sel()
        if not f:
            return
        dlg = FormDialog("Revertir comprobante", [Campo("fecha", "Fecha del contra-asiento", "date", True, defecto=f["fecha"]), Campo("glosa", "Glosa (opcional)", ancho=2)],
                         guardar=lambda v: self.ctx.vouchers.revertir(f["id"], v["fecha"], v["glosa"]),
                         ayuda=f"Se generará un comprobante de traspaso con el debe y el haber invertidos de {f['codigo']}. Ambos permanecen en los libros.",
                         texto_ok="Revertir", parent=self.ventana or self)
        if dlg.exec() == QDialog.Accepted:
            self.refrescar()

    def imprimir(self):
        f = self._sel()
        if f and self.ventana:
            self.ventana.informe("comprobante", {"id": f["id"]}, pedir=False)

    def _reporte(self):
        from ..reports import catalogo
        return catalogo.ejecutar(self.ctx, "control_comprobantes", self._filtros())

    def a_excel(self):
        from PySide6.QtWidgets import QFileDialog
        from ..reports import excel
        ruta, _ = QFileDialog.getSaveFileName(self, "Enviar a Excel", "control_de_comprobantes.xlsx", "Excel (*.xlsx)")
        if ruta and intentar(self, lambda: excel.exportar(self._reporte(), ruta))[0]:
            self._abrir(ruta)

    def a_word(self):
        from PySide6.QtWidgets import QFileDialog
        from ..reports import word
        ruta, _ = QFileDialog.getSaveFileName(self, "Enviar a Word", "control_de_comprobantes.docx", "Word (*.docx)")
        if ruta and intentar(self, lambda: word.exportar(self._reporte(), ruta))[0]:
            self._abrir(ruta)

    @staticmethod
    def _abrir(ruta):
        import os
        if hasattr(os, "startfile"):
            os.startfile(ruta)  # noqa: S606

    def salir(self):
        if self.ventana:
            i = self.ventana.tabs.indexOf(self)
            if i >= 0:
                self.ventana.cerrar_pestana(i)


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
