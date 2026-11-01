"""Registro de comprobantes contables: cabecera ordenada, grilla de campos siempre editables y vínculo con los libros de compras y ventas."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QCompleter, QDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSizePolicy,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..sistema import ErrorNegocio
from ..util import fdate, fmt, parse_num, r2, to_date
from . import iconos, tema
from .calculadora import Calculadora
from .widgets import CampoFecha, CampoImporte, Combo, aviso, boton, confirmar, error, etiqueta, info, intentar


class CampoNavegable(QLineEdit):
    """Campo de la grilla: Enter avanza, flechas arriba/abajo cambian de fila."""
    enter = Signal()
    arriba = Signal()
    abajo = Signal()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.enter.emit()
            return
        if e.key() == Qt.Key_Up and not (self.completer() and self.completer().popup().isVisible()):
            self.arriba.emit()
            return
        if e.key() == Qt.Key_Down and not (self.completer() and self.completer().popup().isVisible()):
            self.abajo.emit()
            return
        super().keyPressEvent(e)

    ultimo = None

    def focusInEvent(self, e):
        super().focusInEvent(e)
        CampoNavegable.ultimo = self
        self.selectAll()


class GridAsiento(QTableWidget):
    """Líneas del asiento. Cada celda es un campo editable permanente (se escribe directamente, sin doble clic).

    Columnas: Código · Nombre de la cuenta · Glosa de la línea · Debe · Haber · equivalentes en la otra moneda.
    Las filas se agregan solas al llenar la última; con Supr se limpia la fila activa."""
    cambio = Signal()
    C_COD, C_NOM, C_GLO, C_DEB, C_HAB, C_EQD, C_EQH = range(7)

    def __init__(self, ctx, filas: int = 12):
        super().__init__(0, 7)
        self.ctx = ctx
        self.moneda = "BS"
        self.tc = 1.0
        self.setHorizontalHeaderLabels(["Código", "Nombre de la cuenta", "Glosa de la línea", "Debe", "Haber", "Debe $us", "Haber $us"])
        h = self.horizontalHeader()
        h.setSectionResizeMode(self.C_NOM, QHeaderView.Stretch)
        h.setSectionResizeMode(self.C_GLO, QHeaderView.Stretch)
        for c, w in ((self.C_COD, 150), (self.C_DEB, 125), (self.C_HAB, 125), (self.C_EQD, 100), (self.C_EQH, 100)):
            h.setSectionResizeMode(c, QHeaderView.Interactive)
            self.setColumnWidth(c, w)
        self.verticalHeader().setDefaultSectionSize(34)
        self.verticalHeader().setVisible(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.cuentas = {c["id"]: c for c in ctx.cuentas.listar(solo_movimiento=True)}
        self.por_codigo = {c["codigo"]: c for c in self.cuentas.values()}
        self.textos = [f"{c['codigo']}  {c['nombre']}" for c in self.cuentas.values()]
        self.setColumnHidden(self.C_GLO, True)
        for _ in range(filas):
            self._nueva_fila()

    # ---------------------------------------------------------------- filas
    def recargar_cuentas(self) -> None:
        self.cuentas = {c["id"]: c for c in self.ctx.cuentas.listar(solo_movimiento=True)}
        self.por_codigo = {c["codigo"]: c for c in self.cuentas.values()}
        self.textos = [f"{c['codigo']}  {c['nombre']}" for c in self.cuentas.values()]
        for r in range(self.rowCount()):
            self._completer(self.cellWidget(r, self.C_COD))

    def _completer(self, w: QLineEdit) -> None:
        c = QCompleter(self.textos, w)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.setFilterMode(Qt.MatchContains)
        c.setMaxVisibleItems(10)
        c.activated.connect(lambda t, w=w: (w.setText(t.split("  ")[0]), w.editingFinished.emit()))
        w.setCompleter(c)

    def _nueva_fila(self) -> int:
        r = self.rowCount()
        self.insertRow(r)
        cod = CampoNavegable()
        cod.setPlaceholderText("código o nombre…")
        self._completer(cod)
        nom = QLabel("")
        nom.setStyleSheet("padding-left:6px;")
        glo = CampoNavegable()
        deb, hab = CampoNavegable(), CampoNavegable()
        for w in (deb, hab):
            w.setAlignment(Qt.AlignRight)
            w.setPlaceholderText("0,00")
        eqd, eqh = QLabel(""), QLabel("")
        for w in (eqd, eqh):
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.setStyleSheet(f"color:{tema.GRIS}; padding-right:6px;")
        for col, w in zip(range(7), (cod, nom, glo, deb, hab, eqd, eqh)):
            self.setCellWidget(r, col, w)
        cod.editingFinished.connect(lambda r=r: self._resolver(r))
        deb.textEdited.connect(lambda _t, r=r: self._exclusivo(r, self.C_DEB))
        hab.textEdited.connect(lambda _t, r=r: self._exclusivo(r, self.C_HAB))
        for w in (deb, hab):
            w.editingFinished.connect(lambda r=r: self._formatear(r))
        for ci, w in enumerate((cod, None, glo, deb, hab)):
            if w is None:
                continue
            w.enter.connect(lambda r=r, ci=ci: self._enter(r, ci))
            w.abajo.connect(lambda r=r, ci=ci: self._ir(r + 1, ci))
            w.arriba.connect(lambda r=r, ci=ci: self._ir(r - 1, ci))
        self.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))
        return r

    def _ir(self, r: int, c: int) -> None:
        if 0 <= r < self.rowCount():
            w = self.cellWidget(r, c)
            if w:
                w.setFocus()

    def _enter(self, r: int, c: int) -> None:
        if c == self.C_COD:
            self._resolver(r)
            self._ir(r, self.C_GLO if not self.isColumnHidden(self.C_GLO) else self.C_DEB)
        elif c == self.C_GLO:
            self._ir(r, self.C_DEB)
        elif c == self.C_DEB:
            self._formatear(r)
            self._ir(r, self.C_HAB if not self.cellWidget(r, self.C_DEB).text() else self.C_COD if False else self.C_HAB)
        else:
            self._formatear(r)
            self._ir(r + 1, self.C_COD)

    def _exclusivo(self, r: int, col: int) -> None:
        otro = self.cellWidget(r, self.C_HAB if col == self.C_DEB else self.C_DEB)
        if self.cellWidget(r, col).text().strip() and otro.text().strip():
            otro.clear()
        self._actualizar(r)

    def _formatear(self, r: int) -> None:
        for c in (self.C_DEB, self.C_HAB):
            w = self.cellWidget(r, c)
            v = parse_num(w.text())
            w.setText(fmt(v) if v else "")
        self._actualizar(r)

    def _resolver(self, r: int) -> None:
        w = self.cellWidget(r, self.C_COD)
        t = w.text().strip()
        cta = self._buscar(t)
        if cta:
            w.setText(cta["codigo"])
            self.cellWidget(r, self.C_NOM).setText(cta["nombre"])
            w.setStyleSheet("")
            w.setProperty("cuenta_id", cta["id"])
        else:
            self.cellWidget(r, self.C_NOM).setText("(cuenta no encontrada)" if t else "")
            w.setStyleSheet(f"color:{tema.ROJO};" if t else "")
            w.setProperty("cuenta_id", None)
        self._actualizar(r)

    def _buscar(self, t: str):
        if not t:
            return None
        if t in self.por_codigo:
            return self.por_codigo[t]
        cod = t.split(" ")[0]
        if cod in self.por_codigo:
            return self.por_codigo[cod]
        tl = t.lower()
        cand = [c for c in self.cuentas.values() if c["codigo"].startswith(t) or tl in c["nombre"].lower()]
        return cand[0] if len(cand) == 1 else None

    def _actualizar(self, r: int) -> None:
        d, h = parse_num(self.cellWidget(r, self.C_DEB).text()), parse_num(self.cellWidget(r, self.C_HAB).text())
        tc = self.tc or 1.0
        if self.moneda == "BS":
            ed, eh = (d / tc, h / tc)
        else:
            ed, eh = (d * tc, h * tc)
        self.cellWidget(r, self.C_EQD).setText(fmt(ed) if d else "")
        self.cellWidget(r, self.C_EQH).setText(fmt(eh) if h else "")
        if r == self.rowCount() - 1 and (self.cellWidget(r, self.C_COD).text() or d or h):
            self._nueva_fila()
        self.cambio.emit()

    def set_moneda(self, moneda: str, tc: float) -> None:
        self.moneda, self.tc = moneda, tc
        self.setHorizontalHeaderLabels(["Código", "Nombre de la cuenta", "Glosa de la línea", "Debe " + ("Bs" if moneda == "BS" else "$us"), "Haber " + ("Bs" if moneda == "BS" else "$us"),
                                        "Debe " + ("$us" if moneda == "BS" else "Bs"), "Haber " + ("$us" if moneda == "BS" else "Bs")])
        for r in range(self.rowCount()):
            self._actualizar(r)

    def limpiar_fila(self, r: int) -> None:
        for c in (self.C_COD, self.C_GLO, self.C_DEB, self.C_HAB):
            self.cellWidget(r, c).clear()
        self._resolver(r)

    def keyPressEvent(self, e):
        super().keyPressEvent(e)

    # ---------------------------------------------------------------- datos
    def fila_activa(self) -> int:
        for r in range(self.rowCount()):
            for c in (self.C_COD, self.C_GLO, self.C_DEB, self.C_HAB):
                w = self.cellWidget(r, c)
                if w and w.hasFocus():
                    return r
        return -1

    def lineas(self) -> list[dict]:
        out = []
        for r in range(self.rowCount()):
            cod = self.cellWidget(r, self.C_COD)
            cta = cod.property("cuenta_id")
            d, h = parse_num(self.cellWidget(r, self.C_DEB).text()), parse_num(self.cellWidget(r, self.C_HAB).text())
            if cod.text().strip() and not cta:
                raise ErrorNegocio(f"Línea {r + 1}: la cuenta «{cod.text()}» no existe o no es de movimiento.")
            if not cta and not d and not h:
                continue
            out.append({"cuenta_id": cta, "glosa": self.cellWidget(r, self.C_GLO).text().strip(), "debe": d, "haber": h})
        return out

    def poner_lineas(self, lineas: list[dict]) -> None:
        self.blockSignals(True)
        while self.rowCount():
            self.removeRow(0)
        for _ in range(max(len(lineas) + 3, 12)):
            self._nueva_fila()
        for r, l in enumerate(lineas):
            c = self.cuentas.get(l["cuenta_id"]) or self.ctx.cuentas.obtener(l["cuenta_id"])
            self.cellWidget(r, self.C_COD).setText(c["codigo"])
            self._resolver(r)
            self.cellWidget(r, self.C_GLO).setText(l.get("glosa") or "")
            self.cellWidget(r, self.C_DEB).setText(fmt(l["debe"]) if l.get("debe") else "")
            self.cellWidget(r, self.C_HAB).setText(fmt(l["haber"]) if l.get("haber") else "")
            self._actualizar(r)
        self.blockSignals(False)
        self.cambio.emit()

    def poner_linea(self, r: int, cuenta_id: int, debe: float = 0.0, haber: float = 0.0) -> None:
        """Atajo para pruebas y para 'Igualar': llena una fila completa."""
        c = self.cuentas[cuenta_id]
        self.cellWidget(r, self.C_COD).setText(c["codigo"])
        self._resolver(r)
        self.cellWidget(r, self.C_DEB).setText(fmt(debe) if debe else "")
        self.cellWidget(r, self.C_HAB).setText(fmt(haber) if haber else "")
        self._actualizar(r)


class FacturaVinculoDialog(QDialog):
    """«¿Existe factura?»: datos de la factura que alimenta el libro de compras (egreso) o de ventas (ingreso)."""

    def __init__(self, ctx, tipo: str, fecha, importe_sugerido: float, razon: str = "", parent=None):
        super().__init__(parent)
        self.ctx, self.tipo = ctx, tipo
        compra = tipo == "E"
        self.setWindowTitle("Factura del comprobante")
        self.setMinimumWidth(640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(8)
        h = QLabel("Factura de compra → Libro de Compras (crédito fiscal)" if compra else "Factura de venta → Libro de Ventas (débito fiscal)")
        h.setObjectName("h1")
        lay.addWidget(h)
        a = QLabel("Los datos se registrarán en el libro IVA del período del comprobante y quedarán vinculados a él.")
        a.setObjectName("sub")
        lay.addWidget(a)
        self.modo = Combo([("N", "Compra de mercado interno (factura)"), ("I", "Importación (DUI)")]) if compra else None
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        self.nit, self.razon, self.nro, self.aut, self.dui = QLineEdit(), QLineEdit(razon), QLineEdit(), QLineEdit(), QLineEdit()
        self.total = CampoImporte(importe_sugerido)
        self.nosuj, self.desc = CampoImporte(0.0), CampoImporte(0.0)
        self.lbl = QLabel("")
        self.lbl.setStyleSheet(f"font-weight:600; color:{tema.AZUL};")
        campos = [("NIT / CI del " + ("proveedor" if compra else "cliente"), self.nit), ("Razón social", self.razon), ("Nº de factura", self.nro), ("Nº de autorización / CUF", self.aut),
                  ("Importe total de la factura", self.total), ("Importe no sujeto a " + ("crédito" if compra else "débito") + " fiscal", self.nosuj), ("Descuentos", self.desc)]
        if compra:
            campos.insert(0, ("Tipo de compra", self.modo))
            campos.insert(3, ("Nº de DUI (solo importación)", self.dui))
        for i, (et, w) in enumerate(campos):
            g.addWidget(etiqueta(et), (i // 2) * 2, i % 2)
            g.addWidget(w, (i // 2) * 2 + 1, i % 2)
        lay.addLayout(g)
        self.agregar = QCheckBox("Agregar al comprobante la línea de " + ("crédito" if compra else "débito") + " fiscal IVA (separándola del importe principal)")
        self.agregar.setChecked(True)
        lay.addWidget(self.agregar)
        lay.addWidget(self.lbl)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)
        ok, no, ca = boton("Aceptar", "primario", 110), boton("Cancelar", "", 100), None
        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(no)
        fila.addWidget(ok)
        lay.addLayout(fila)
        ok.clicked.connect(self.validar)
        no.clicked.connect(self.reject)
        self.fecha = to_date(fecha)
        for w in (self.total, self.nosuj, self.desc):
            w.cambiado.connect(lambda *_: self.calc())
        self.calc()

    def datos(self) -> dict:
        d = {"nit": self.nit.text().strip(), "razon_social": self.razon.text().strip(), "nro_factura": self.nro.text().strip(), "nro_autorizacion": self.aut.text().strip(),
             "importe_total": self.total.valor(), "no_sujeto": self.nosuj.valor(), "descuentos": self.desc.valor()}
        if self.modo and self.modo.valor() == "I":
            d["dui"] = self.dui.text().strip()
            d["tipo_compra"] = 1
            if not d["nro_factura"]:
                d["nro_factura"] = d["dui"]
        return d

    def calc(self) -> None:
        try:
            c = self.ctx.iva.calcular({**self.datos(), "fecha": self.fecha})
            self.lbl.setText(f"Importe base: {fmt(c['base_iva'])}      {'Crédito' if self.tipo == 'E' else 'Débito'} fiscal (13%): {fmt(c['iva'])}")
            self.err.setText("")
        except Exception as ex:  # noqa: BLE001
            self.err.setText(str(ex))

    def validar(self) -> None:
        d = self.datos()
        if not d["nro_factura"]:
            self.err.setText("Indique el número de factura (o de DUI en importaciones).")
            return
        if not d["nit"] and self.tipo == "E":
            self.err.setText("Indique el NIT del proveedor.")
            return
        if d["importe_total"] <= 0:
            self.err.setText("El importe de la factura debe ser mayor a cero.")
            return
        self.accept()


class PlanCuentasDialog(QDialog):
    """Acceso directo al plan de cuentas desde el comprobante: crear o modificar cuentas sin salir del registro."""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        from .p_contab import PlanCuentasPantalla
        self.setWindowTitle("Plan de cuentas")
        self.resize(980, 620)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(PlanCuentasPantalla(ctx, None))


class ComprobanteDialog(QDialog):
    def __init__(self, ctx, cid: int | None, parent=None, previo: dict | None = None):
        super().__init__(parent)
        self.ctx, self.cid = ctx, cid
        self.vent = parent
        self.factura = None
        comp = ctx.vouchers.obtener(cid) if cid else None
        self.comp = comp
        self.solo_lectura = bool(comp and (comp["estado"] != "V" or comp["origen"] not in ("MANUAL", "COMPROBANTE") or not ctx.puede("CONT.COMPROBANTES"))) or not ctx.abierta
        self.setWindowTitle("Introducción de comprobantes")
        self.setWindowIcon(tema.icono_app())
        self.resize(1120, 720)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        # ---- franja superior
        franja = QFrame()
        franja.setObjectName("banner")
        fl = QHBoxLayout(franja)
        fl.setContentsMargins(22, 12, 22, 10)
        ic = QLabel()
        ic.setPixmap(iconos.icono("comprobante", "conta", 40).pixmap(40, 40))
        self.l_titulo = QLabel("Comprobante contable")
        self.l_titulo.setObjectName("h1")
        self.l_sub = QLabel("")
        self.l_sub.setObjectName("sub")
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(self.l_titulo)
        col.addWidget(self.l_sub)
        fl.addWidget(ic)
        fl.addSpacing(10)
        fl.addLayout(col, 1)
        self.b_calc = boton("Calculadora")
        self.b_calc.setIcon(iconos.icono("calculadora", "admin", 22, True))
        self.b_plan = boton("Plan de cuentas")
        self.b_plan.setIcon(iconos.icono("plan", "conta", 22, True))
        fl.addWidget(self.b_calc)
        fl.addWidget(self.b_plan)
        lay.addWidget(franja)
        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(20, 12, 20, 14)
        cuerpo.setSpacing(10)
        lay.addLayout(cuerpo, 1)
        # ---- cabecera en tarjeta
        tarjeta = QFrame()
        tarjeta.setObjectName("panel")
        g = QGridLayout(tarjeta)
        g.setContentsMargins(16, 12, 16, 12)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(4)
        tipos = [(x["codigo"], f"{x['nombre']}") for x in ctx.vouchers.tipos() if x["codigo"] in ("I", "E", "T", "AJ")]
        self.tipo = Combo(tipos)
        self.tipo.setMinimumWidth(120)
        self.num = QLineEdit()
        self.num.setReadOnly(True)
        self.num.setAlignment(Qt.AlignCenter)
        self.num.setMaximumWidth(120)
        self.fecha = CampoFecha(comp["fecha"] if comp else (previo or {}).get("fecha") or min(max(date.today(), ctx.inicio), ctx.fin), ctx.inicio, ctx.fin)
        self.fecha.setMaximumWidth(125)
        self.moneda = Combo([("BS", "Bs"), ("USD", "US$")])
        self.moneda.setMaximumWidth(80)
        self.tc = CampoImporte(ctx.tc.dolar(self.fecha.fecha()), 4)
        self.tc.setMaximumWidth(88)
        self.ufv = CampoImporte(ctx.tc.ufv(self.fecha.fecha()), 5)
        self.ufv.setMaximumWidth(105)
        self.banco = Combo()
        self.banco.cargar([(c["id"], f"{c['codigo']}  {c['nombre']}") for c in ctx.bancos.cuentas_banco() if c["es_banco"]], "(sin banco)")
        self.cheque = QLineEdit()
        self.cheque.setPlaceholderText("Nº de cheque / depósito")
        self.cheque.setMaximumWidth(190)
        self.glosa = QLineEdit(comp["glosa"] if comp else "")
        self.glosa.setPlaceholderText("Descripción general del comprobante")
        self.glosa_linea = QCheckBox("Glosa por línea")
        self.nombre = QLineEdit(comp["a_nombre"] or "" if comp else "")
        self.nombre.setPlaceholderText("Pagado a / recibido de / cancelado a")
        self.nro = QLineEdit(comp["nro_doc"] or "" if comp else "")
        self.nro.setPlaceholderText("Factura, recibo…")
        self.nro.setMaximumWidth(190)
        self.l_mes = QLabel("")
        self.l_mes.setStyleSheet(f"color:{tema.AZUL}; font-weight:600;")
        cab1 = [("Tipo de comprobante", self.tipo), ("Nº (automático)", self.num), ("Fecha", self.fecha), ("Mes", self.l_mes), ("Moneda", self.moneda), ("T.C.", self.tc), ("UFV", self.ufv)]
        for i, (et, w) in enumerate(cab1):
            g.addWidget(etiqueta(et), 0, i)
            g.addWidget(w, 1, i)
        g.setColumnStretch(7, 1)
        self.l_banco = etiqueta("Banco")
        self.l_cheque = etiqueta("Nº cheque / depósito")
        g.addWidget(self.l_banco, 2, 0, 1, 3)
        g.addWidget(self.banco, 3, 0, 1, 3)
        g.addWidget(self.l_cheque, 2, 3, 1, 3)
        g.addWidget(self.cheque, 3, 3, 1, 3)
        g.addWidget(self.glosa_linea, 3, 6, 1, 2)
        g.addWidget(etiqueta("Glosa *"), 4, 0, 1, 8)
        g.addWidget(self.glosa, 5, 0, 1, 8)
        self.l_nombre = etiqueta("Cancelado a / recibido de")
        g.addWidget(self.l_nombre, 6, 0, 1, 5)
        g.addWidget(etiqueta("Nº de documento"), 6, 5, 1, 3)
        g.addWidget(self.nombre, 7, 0, 1, 5)
        g.addWidget(self.nro, 7, 5, 1, 3)
        cuerpo.addWidget(tarjeta)
        # ---- asiento
        self.grid = GridAsiento(ctx)
        cuerpo.addWidget(self.grid, 1)
        ayuda = QLabel("Escriba el código o parte del nombre de la cuenta y pulse Enter. Las filas se agregan solas. Supr limpia la fila activa.")
        ayuda.setObjectName("sub")
        cuerpo.addWidget(ayuda)
        # ---- totales
        tot = QHBoxLayout()
        self.b_igualar = boton("Igualar")
        self.b_igualar.setToolTip("Coloca la diferencia en la línea activa (o en una nueva línea con la cuenta del banco)")
        tot.addWidget(self.b_igualar)
        tot.addStretch(1)
        self.l_debe, self.l_haber, self.l_dif = QLabel(), QLabel(), QLabel()
        for l in (self.l_debe, self.l_haber, self.l_dif):
            l.setStyleSheet("font-size:11pt; font-weight:600; padding:0 14px;")
            tot.addWidget(l)
        cuerpo.addLayout(tot)
        self.l_fac = QLabel("")
        self.l_fac.setStyleSheet(f"color:{tema.VERDE};")
        cuerpo.addWidget(self.l_fac)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        cuerpo.addWidget(self.err)
        # ---- botones
        pie = QHBoxLayout()
        self.b_print = boton("Imprimir")
        self.b_anular = boton("Anular comprobante", "peligro")
        self.b_close = boton("Cancelar")
        self.b_ok = boton("Grabar", "primario", 130)
        pie.addWidget(self.b_anular)
        pie.addWidget(self.b_print)
        pie.addStretch(1)
        pie.addWidget(self.b_close)
        pie.addWidget(self.b_ok)
        cuerpo.addLayout(pie)
        # ---- conexiones
        self.b_calc.clicked.connect(self.calculadora)
        self.b_plan.clicked.connect(self.plan)
        self.b_igualar.clicked.connect(self.igualar)
        self.b_ok.clicked.connect(self.grabar)
        self.b_close.clicked.connect(self.reject)
        self.b_print.clicked.connect(self.imprimir)
        self.b_anular.clicked.connect(self.anular)
        self.grid.cambio.connect(self.totales)
        self.tipo.currentIndexChanged.connect(self._tipo)
        self.fecha.dateChanged.connect(self._fecha)
        self.moneda.currentIndexChanged.connect(self._moneda)
        self.tc.cambiado.connect(lambda *_: self._moneda())
        self.glosa_linea.toggled.connect(lambda v: self.grid.setColumnHidden(GridAsiento.C_GLO, not v))
        if comp:
            self.tipo.set_valor(comp["tipo"])
            self.moneda.set_valor(comp["moneda"])
            self.tc.set_valor(comp["tc"])
            self.ufv.set_valor(comp["ufv"] or ctx.tc.ufv(comp["fecha"]))
            if comp["banco_id"]:
                self.banco.set_valor(comp["banco_id"])
            self.cheque.setText(comp["nro_cheque"] or "")
            self.glosa_linea.setChecked(bool(comp["glosa_por_linea"]))
            usd = comp["moneda"] == "USD"
            self.grid.set_moneda(comp["moneda"], comp["tc"])
            self.grid.poner_lineas([{**l, "debe": l["debe_usd"] if usd else l["debe_bs"], "haber": l["haber_usd"] if usd else l["haber_bs"]} for l in comp["lineas"]])
            fv = ctx.vouchers.factura_vinculada(cid)
            if fv:
                self.l_fac.setText(f"Factura vinculada: Nº {fv['nro_factura']} · {fv['razon_social']} · IVA Bs {fmt(fv['iva'])} (Libro de {'Compras' if fv['libro'] == 'C' else 'Ventas'})")
        elif previo and previo.get("lineas"):
            self.grid.poner_lineas(previo["lineas"])
        self._tipo()
        self._fecha(solo_numero=bool(comp))
        self.l_titulo.setText("Comprobante " + ctx.vouchers.codigo(comp) if comp else "Introducción de comprobante")
        self.l_sub.setText(("Anulado · " if comp and comp["estado"] == "A" else "") + (f"Generado por el módulo {comp['origen']} (solo consulta)" if comp and comp["origen"] not in ("MANUAL", "COMPROBANTE")
                                                                                       else "Registre el asiento contable: es la fuente de los estados financieros"))
        self.b_print.setVisible(bool(comp))
        self.b_anular.setVisible(bool(comp and comp["estado"] == "V" and ctx.puede("CONT.ANULAR") and ctx.abierta))
        if self.solo_lectura:
            for w in (self.tipo, self.fecha, self.moneda, self.tc, self.ufv, self.banco, self.cheque, self.glosa, self.glosa_linea, self.nombre, self.nro, self.grid, self.b_ok, self.b_igualar):
                w.setEnabled(False)
        self.totales()
        (self.grid._ir(0, GridAsiento.C_COD) if not comp else self.b_close.setFocus())
        if not comp:
            self.glosa.setFocus()
        self._calc = None

    # ----------------------------------------------------------- cabecera
    def _tipo(self) -> None:
        t = self.tipo.valor()
        banco_visible = t in ("E", "I")
        for w in (self.l_banco, self.banco, self.l_cheque, self.cheque):
            w.setVisible(banco_visible)
        self.l_cheque.setText("Nº de cheque" if t == "E" else "Nº de depósito / transferencia")
        self.l_nombre.setText("Cancelado a" if t == "E" else "Recibido de" if t == "I" else "A nombre de")
        self._fecha(solo_numero=bool(self.comp and self.comp["tipo"] == t))

    def _fecha(self, *_a, solo_numero: bool = False) -> None:
        f = self.fecha.fecha()
        self.l_mes.setText(f"{f.month:02d}")
        if self.comp and self.comp["tipo"] == self.tipo.valor() and self.comp["mes"] == f.month:
            self.num.setText(self.ctx.vouchers.codigo(self.comp))
        else:
            self.num.setText(self.ctx.vouchers.siguiente_numero(self.tipo.valor(), f)[1])
        if not self.comp or not solo_numero:
            self.tc.set_valor(self.ctx.tc.dolar(f))
            self.ufv.set_valor(self.ctx.tc.ufv(f))
        self._moneda()

    def _moneda(self) -> None:
        self.grid.set_moneda(self.moneda.valor(), self.tc.valor() or 1.0)

    # ------------------------------------------------------------ utilidades
    def calculadora(self) -> None:
        if self._calc is None or not self._calc.isVisible():
            self._calc = Calculadora(self)
            self._calc.resultado.connect(self._pegar)
        self._calc.show()
        self._calc.raise_()

    def _pegar(self, v: float) -> None:
        w = CampoNavegable.ultimo
        if w is not None and w.isVisible() and w.alignment() & Qt.AlignRight:
            w.setText(fmt(v))
            w.textEdited.emit(w.text())
            w.editingFinished.emit()

    def plan(self) -> None:
        PlanCuentasDialog(self.ctx, self).exec()
        self.grid.recargar_cuentas()

    def igualar(self) -> None:
        d = sum(parse_num(self.grid.cellWidget(r, GridAsiento.C_DEB).text()) for r in range(self.grid.rowCount()))
        h = sum(parse_num(self.grid.cellWidget(r, GridAsiento.C_HAB).text()) for r in range(self.grid.rowCount()))
        dif = r2(d - h)
        if abs(dif) < 0.005:
            return
        r = self.grid.fila_activa()
        # fila de destino: la activa si está vacía de importes; si no, la primera fila vacía
        def libre(i: int) -> bool:
            return not parse_num(self.grid.cellWidget(i, GridAsiento.C_DEB).text()) and not parse_num(self.grid.cellWidget(i, GridAsiento.C_HAB).text())
        if r < 0 or not libre(r):
            r = next(i for i in range(self.grid.rowCount()) if libre(i))
        col = GridAsiento.C_HAB if dif > 0 else GridAsiento.C_DEB
        if not self.grid.cellWidget(r, GridAsiento.C_COD).text() and self.banco.valor():
            self.grid.poner_linea(r, self.banco.valor())
        self.grid.cellWidget(r, col).setText(fmt(abs(dif)))
        self.grid._actualizar(r)

    def totales(self) -> None:
        d = h = 0.0
        for r in range(self.grid.rowCount()):
            d += parse_num(self.grid.cellWidget(r, GridAsiento.C_DEB).text())
            h += parse_num(self.grid.cellWidget(r, GridAsiento.C_HAB).text())
        d, h = r2(d), r2(h)
        dif = r2(d - h)
        self.l_debe.setText(f"Debe: {fmt(d)}")
        self.l_haber.setText(f"Haber: {fmt(h)}")
        ok = abs(dif) < 0.005 and d > 0
        self.l_dif.setText("✔ Cuadra" if ok else f"Diferencia: {fmt(dif)}")
        self.l_dif.setStyleSheet(f"font-size:11pt; font-weight:600; padding:0 14px; color:{tema.VERDE if ok else tema.ROJO};")

    # ------------------------------------------------------------- grabar
    def _datos(self, lineas: list[dict]) -> dict:
        return {"tipo": self.tipo.valor(), "fecha": self.fecha.fecha(), "glosa": self.glosa.text(), "moneda": self.moneda.valor(), "tc": self.tc.valor(), "ufv": self.ufv.valor(),
                "a_nombre": self.nombre.text().strip() or None, "nro_doc": self.nro.text().strip() or None, "banco_id": self.banco.valor() if self.tipo.isVisible() else None,
                "nro_cheque": self.cheque.text().strip() if self.cheque.isVisible() else None, "glosa_por_linea": self.glosa_linea.isChecked(), "lineas": lineas}

    def _preguntar_factura(self, lineas: list[dict]) -> tuple[list[dict], dict | None] | None:
        """Orion pregunta «¿Existe factura?» al grabar egresos/ingresos. Devuelve (líneas, factura) o None si se cancela."""
        t = self.tipo.valor()
        if t not in ("E", "I") or (self.comp and self.ctx.vouchers.factura_vinculada(self.cid)):
            return lineas, None
        cta_cf, cta_df = self.ctx.cuenta_param("CTA_CF_IVA"), self.ctx.cuenta_param("CTA_DF_IVA")
        if any(l["cuenta_id"] in (cta_cf, cta_df) for l in lineas) and self.comp:
            return lineas, None
        m = QMessageBox(self)
        m.setIcon(QMessageBox.Question)
        m.setWindowTitle("Facturas")
        m.setText("<b>¿Existe factura?</b>")
        m.setInformativeText("Si existe, se registrará en el " + ("Libro de Compras" if t == "E" else "Libro de Ventas") + " vinculada a este comprobante.")
        si, no = m.addButton("Sí, hay factura", QMessageBox.YesRole), m.addButton("No", QMessageBox.NoRole)
        cancel = m.addButton("Volver", QMessageBox.RejectRole)
        m.exec()
        if m.clickedButton() is cancel:
            return None
        if m.clickedButton() is no:
            return lineas, None
        base = sum(l["debe"] for l in lineas if l["cuenta_id"] not in (cta_cf, cta_df)) if t == "E" else sum(l["haber"] for l in lineas if l["cuenta_id"] not in (cta_cf, cta_df))
        dlg = FacturaVinculoDialog(self.ctx, t, self.fecha.fecha(), r2(base), self.nombre.text(), self)
        if dlg.exec() != QDialog.Accepted:
            return None
        fac = dlg.datos()
        if dlg.agregar.isChecked():
            lineas = self.ctx.vouchers.ajustar_asiento_iva(t, lineas, fac["importe_total"], self.fecha.fecha())
            self.grid.poner_lineas(lineas)
        return lineas, fac

    def grabar(self) -> None:
        self.err.setText("")
        try:
            lineas = self.grid.lineas()
            if len(lineas) < 2:
                raise ErrorNegocio("Registre al menos dos líneas con cuenta e importe.")
            if not self.glosa.text().strip():
                self.glosa.setFocus()
                raise ErrorNegocio("La glosa del comprobante es obligatoria.")
            d0 = r2(sum(l["debe"] for l in lineas)) - r2(sum(l["haber"] for l in lineas))
            if abs(d0) > 0.005 and self.moneda.valor() == "BS":
                raise ErrorNegocio(f"El comprobante no cuadra: la diferencia es {fmt(abs(d0))}. Use «Igualar» o corrija los importes.")
            r = self._preguntar_factura(lineas)
            if r is None:
                return
            lineas, fac = r
            datos = self._datos(lineas)
            if fac:
                datos["factura"] = fac
            if self.cid:
                self.ctx.vouchers.modificar(self.cid, datos)
            else:
                self.cid = self.ctx.vouchers.crear(datos)
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
        if confirmar(self, "¿Anular este comprobante? Dejará de afectar los saldos y su factura vinculada (si existe) se anulará.", "Anular comprobante", True):
            ok, _ = intentar(self, self.ctx.vouchers.anular, self.cid)
            if ok:
                self.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            r = self.grid.fila_activa()
            if r >= 0:
                self.grid.limpiar_fila(r)
                return
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            return  # Enter navega entre campos; no cierra el diálogo
        super().keyPressEvent(e)
