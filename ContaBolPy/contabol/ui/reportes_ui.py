"""Visor de informes (pantalla), parámetros y exportación a PDF/Excel; centro de reportes."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import date

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QScrollArea, QSplitter,
                               QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QSpinBox, QCheckBox)

from ..reports import catalogo, excel, pdf
from ..reports.engine import ReporteDef, Tabla, Texto
from ..util import fmt, to_date
from . import tema
from .base import Pantalla
from .widgets import CampoFecha, CampoImporte, Combo, aviso, boton, error, etiqueta, hbox, info, intentar


def abrir_archivo(ruta: str) -> None:
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # type: ignore[attr-defined]


def carpeta_reportes(ctx) -> str:
    d = os.path.join(ctx.sistema.raiz, "reportes")
    os.makedirs(d, exist_ok=True)
    return d


class VisorInforme(Pantalla):
    """Vista previa en pantalla del informe, con exportación a PDF, Excel e impresión."""

    def __init__(self, ctx, rep: ReporteDef, ventana=None, regenerar=None):
        self.rep = rep
        self.titulo = rep.titulo
        self.subtitulo = " · ".join(x for x in (rep.subtitulo, rep.periodo, rep.moneda) if x)
        super().__init__(ctx, ventana)
        self.regenerar = regenerar
        b_pdf = boton("PDF", "primario", 90)
        b_xls = boton("Excel", "exito", 90)
        b_imp = boton("Imprimir", "", 90)
        for b in (b_imp, b_xls, b_pdf):
            self.banner.agregar(b)
        b_pdf.clicked.connect(self.guardar_pdf)
        b_xls.clicked.connect(self.guardar_excel)
        b_imp.clicked.connect(self.imprimir)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        cont = QWidget()
        self.vl = QVBoxLayout(cont)
        self.vl.setContentsMargins(0, 0, 0, 0)
        self.vl.setSpacing(10)
        area.setWidget(cont)
        self.cuerpo.addWidget(area, 1)
        self._dibujar()

    def _dibujar(self) -> None:
        for b in self.rep.bloques:
            if isinstance(b, Texto):
                if b.estilo == "salto":
                    ln = QFrame()
                    ln.setFrameShape(QFrame.HLine)
                    ln.setStyleSheet(f"color:{tema.BORDE};")
                    self.vl.addWidget(ln)
                    continue
                l = QLabel(b.texto)
                l.setWordWrap(True)
                if b.estilo == "titulo":
                    l.setStyleSheet(f"font-weight:600; color:{tema.AZUL}; font-size:11pt; margin-top:8px;")
                self.vl.addWidget(l)
                continue
            t: Tabla = b
            if t.titulo:
                l = QLabel(t.titulo)
                l.setStyleSheet(f"font-weight:600; color:{tema.AZUL}; margin-top:6px;")
                self.vl.addWidget(l)
            tb = QTableWidget(len(t.filas), len(t.cols))
            tb.setHorizontalHeaderLabels([c.titulo for c in t.cols])
            tb.horizontalHeader().setVisible(not t.sin_encabezado)
            tb.verticalHeader().setVisible(False)
            tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tb.setAlternatingRowColors(True)
            tb.setShowGrid(False)
            tb.verticalHeader().setDefaultSectionSize(26)
            h = tb.horizontalHeader()
            principal = max(range(len(t.cols)), key=lambda k: (t.cols[k].tipo == "txt", t.cols[k].ancho))
            for i, c in enumerate(t.cols):
                if i == principal:
                    h.setSectionResizeMode(i, QHeaderView.Stretch)
                else:
                    h.setSectionResizeMode(i, QHeaderView.Interactive)
                    base = {"money": 128, "num": 104, "int": 72, "pct": 90, "date": 100}.get(c.tipo, 120)
                    tb.setColumnWidth(i, int(max(base, min(c.ancho * 62, 230))))
            for r, f in enumerate(t.filas):
                for i, c in enumerate(t.cols):
                    v = f.valores[i] if i < len(f.valores) else None
                    txt = self._txt(v, c)
                    if i == 0 and f.nivel:
                        txt = "    " * f.nivel + txt
                    it = QTableWidgetItem(txt)
                    if c.tipo in ("money", "num", "int", "pct"):
                        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        if isinstance(v, (int, float)) and v < 0:
                            it.setForeground(Qt.red)
                    if f.estilo in ("titulo", "total", "subtotal", "grupo"):
                        fnt = it.font()
                        fnt.setBold(True)
                        it.setFont(fnt)
                    if f.estilo in ("titulo", "total"):
                        it.setBackground(self._color(tema.AZUL_CLARO))
                    tb.setItem(r, i, it)
            alto = (0 if t.sin_encabezado else 32) + 26 * len(t.filas) + 6
            tb.setFixedHeight(min(max(alto, 60), 4000))
            tb.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.vl.addWidget(tb)
        for n in self.rep.notas:
            l = QLabel(n)
            l.setObjectName("sub")
            l.setWordWrap(True)
            self.vl.addWidget(l)
        self.vl.addStretch(1)

    @staticmethod
    def _color(hex_):
        from PySide6.QtGui import QColor
        return QColor(hex_)

    @staticmethod
    def _txt(v, c) -> str:
        if v is None or v == "":
            return ""
        if c.tipo in ("money", "num"):
            return fmt(v, c.decimales)
        if c.tipo == "int":
            return f"{int(v):,}".replace(",", ".")
        if c.tipo == "pct":
            return fmt(v, 2) + "%"
        return str(v)

    def _nombre(self) -> str:
        n = self.rep.nombre_archivo or "informe"
        return f"{n}_{date.today():%Y%m%d}"

    def guardar_pdf(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar informe en PDF", os.path.join(carpeta_reportes(self.ctx), self._nombre() + ".pdf"), "PDF (*.pdf)")
        if not ruta:
            return
        ok, _ = intentar(self, pdf.exportar, self.rep, ruta)
        if ok:
            abrir_archivo(ruta)

    def guardar_excel(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar a Excel", os.path.join(carpeta_reportes(self.ctx), self._nombre() + ".xlsx"), "Excel (*.xlsx)")
        if not ruta:
            return
        ok, _ = intentar(self, excel.exportar, self.rep, ruta)
        if ok:
            abrir_archivo(ruta)

    def imprimir(self) -> None:
        ruta = os.path.join(tempfile.gettempdir(), f"contabol_{self._nombre()}.pdf")
        ok, _ = intentar(self, pdf.exportar, self.rep, ruta)
        if not ok:
            return
        if sys.platform.startswith("win"):
            try:
                os.startfile(ruta, "print")  # type: ignore[attr-defined]
                return
            except OSError:
                pass
        abrir_archivo(ruta)


class ParametrosDialog(QDialog):
    """Pide los parámetros de un informe del catálogo."""

    def __init__(self, ctx, rep: catalogo.ReporteCat, parent=None):
        super().__init__(parent)
        self.ctx, self.rep = ctx, rep
        self.setWindowTitle(rep.titulo)
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        h = QLabel(rep.titulo)
        h.setObjectName("h1")
        lay.addWidget(h)
        if rep.descripcion:
            d = QLabel(rep.descripcion)
            d.setObjectName("sub")
            d.setWordWrap(True)
            lay.addWidget(d)
        self.w: dict[str, QWidget] = {}
        vals = catalogo.valores_defecto(ctx, rep)
        for p in rep.params:
            lay.addWidget(etiqueta(p.titulo))
            w = self._crear(p, vals.get(p.clave))
            self.w[p.clave] = w
            lay.addWidget(w)
        b_ver, b_c = boton("Ver informe", "primario", 130), boton("Cancelar")
        lay.addSpacing(8)
        lay.addLayout(hbox(None, b_c, b_ver))
        b_ver.clicked.connect(self.accept)
        b_c.clicked.connect(self.reject)

    def _crear(self, p: catalogo.ParamDef, v):
        c = self.ctx
        t = p.tipo
        if t in ("desde", "hasta", "fecha"):
            return CampoFecha(v, c.inicio, c.fin)
        if t == "mes":
            w = Combo([(i, n) for i, n in enumerate(["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]) if i])
            w.set_valor(int(v or 1))
            return w
        if t == "nivel":
            w = QSpinBox()
            w.setRange(1, 6)
            w.setValue(int(v or 5))
            return w
        if t == "moneda":
            return self._combo([("BS", "Bolivianos (Bs)"), ("USD", "Dólares (US$)")], v)
        if t == "bool":
            w = QCheckBox("Sí")
            w.setChecked(bool(v))
            return w
        if t == "cuenta":
            return self._combo([(x["id"], f"{x['codigo']}  {x['nombre']}") for x in c.cuentas.listar(solo_movimiento=True)], v, None)
        if t in ("tercero", "tercero_c", "tercero_p"):
            return self._combo([(x["id"], f"{x['nombre']}") for x in c.terceros.listar(solo_activos=False)], v, None)
        if t == "item":
            return self._combo([(x["id"], f"{x['codigo']}  {x['nombre']}") for x in c.inventario.items(solo_activos=False)], v, None)
        if t == "empleado":
            return self._combo([(x["id"], f"{x['nombre']}") for x in c.rrhh.empleados(False)], v, "(todos)" if not p.requerido else None)
        if t == "almacen":
            return self._combo([(x["id"], x["nombre"]) for x in c.inventario.catalogo("almacen")], v, "(todos)")
        if t == "orden":
            return self._combo([(x["id"], f"Nº {x['numero']} - {x['item_nombre']}") for x in c.produccion.listar()], v, None)
        if t == "comprobante":
            return self._combo([(x["id"], f"{c.vouchers.codigo(x)}  {x['glosa'][:50]}") for x in c.vouchers.listar()], v, None)
        if t == "tipo_comp":
            return self._combo([(x["codigo"], x["nombre"]) for x in c.vouchers.tipos()], v, "(todos)")
        if t == "lista":
            return self._combo(p.opciones or [], v)
        if t in ("entero", "importe"):
            w = CampoImporte(float(v or 0), 0 if t == "entero" else 2)
            return w
        return QLineEdit(str(v or ""))

    @staticmethod
    def _combo(ops, v, vacio=None):
        w = Combo()
        w.cargar(ops, vacio)
        if v is not None:
            w.set_valor(v)
        return w

    def valores(self) -> dict:
        out = {}
        for p in self.rep.params:
            w = self.w[p.clave]
            if isinstance(w, CampoFecha):
                out[p.clave] = w.fecha()
            elif isinstance(w, Combo):
                out[p.clave] = w.valor()
            elif isinstance(w, QSpinBox):
                out[p.clave] = w.value()
            elif isinstance(w, QCheckBox):
                out[p.clave] = w.isChecked()
            elif isinstance(w, CampoImporte):
                out[p.clave] = w.valor() if p.tipo == "importe" else int(w.valor())
            else:
                out[p.clave] = w.text().strip()
        return out


def abrir_informe(ventana, ctx, id_: str, valores: dict | None = None, pedir: bool = True) -> None:
    rep = catalogo.buscar(id_)
    if not ctx.puede(rep.permiso):
        aviso(ventana, "No tiene permiso para este informe.")
        return
    vals = valores
    if pedir and rep.params and valores is None:
        dlg = ParametrosDialog(ctx, rep, ventana)
        if dlg.exec() != QDialog.Accepted:
            return
        vals = dlg.valores()
    ok, r = intentar(ventana, catalogo.ejecutar, ctx, id_, vals)
    if ok:
        ventana.abrir_pantalla(VisorInforme(ctx, r, ventana), clave=None, titulo=rep.titulo)


class CentroReportes(Pantalla):
    titulo = "Centro de reportes"
    subtitulo = "Todos los informes del sistema por módulo. Cada uno se puede ver en pantalla, guardar en PDF, exportar a Excel o imprimir."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar informe por nombre o módulo…")
        self.buscar.setClearButtonEnabled(True)
        self.cuerpo.addWidget(self.buscar)
        sp = QSplitter()
        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.setIndentation(18)
        self.arbol.setStyleSheet("QTreeWidget { font-size: 10.5pt; } QTreeWidget::item { padding: 4px; }")
        sp.addWidget(self.arbol)
        der = QFrame()
        der.setObjectName("panel")
        dl = QVBoxLayout(der)
        dl.setContentsMargins(20, 18, 20, 18)
        self.l_tit = QLabel("Seleccione un informe")
        self.l_tit.setObjectName("h1")
        self.l_tit.setWordWrap(True)
        self.l_desc = QLabel("")
        self.l_desc.setWordWrap(True)
        self.l_desc.setAlignment(Qt.AlignTop)
        self.b_abrir = boton("Abrir informe", "primario", 160)
        self.b_abrir.setEnabled(False)
        dl.addWidget(self.l_tit)
        dl.addWidget(self.l_desc, 1)
        dl.addWidget(self.b_abrir, 0, Qt.AlignLeft)
        sp.addWidget(der)
        sp.setStretchFactor(0, 3)
        sp.setStretchFactor(1, 2)
        self.cuerpo.addWidget(sp, 1)
        self.buscar.textChanged.connect(self.llenar)
        self.arbol.itemSelectionChanged.connect(self.describir)
        self.arbol.itemDoubleClicked.connect(lambda *_: self.abrir())
        self.b_abrir.clicked.connect(self.abrir)
        self.llenar()

    def llenar(self) -> None:
        f = self.buscar.text().strip().lower()
        self.arbol.clear()
        grupos: dict[str, QTreeWidgetItem] = {}
        for r in sorted(catalogo.todos(), key=lambda x: (x.modulo, x.titulo)):
            if not self.ctx.puede(r.permiso) or (f and f not in r.titulo.lower() and f not in r.modulo.lower()):
                continue
            g = grupos.get(r.modulo)
            if not g:
                g = QTreeWidgetItem([r.modulo])
                fnt = g.font(0)
                fnt.setBold(True)
                g.setFont(0, fnt)
                self.arbol.addTopLevelItem(g)
                grupos[r.modulo] = g
            it = QTreeWidgetItem([r.titulo])
            it.setData(0, Qt.UserRole, r.id)
            g.addChild(it)
        self.arbol.expandAll()

    def _sel(self):
        it = self.arbol.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def describir(self) -> None:
        id_ = self._sel()
        if not id_:
            self.b_abrir.setEnabled(False)
            return
        r = catalogo.buscar(id_)
        self.l_tit.setText(r.titulo)
        self.l_desc.setText(f"Módulo: {r.modulo}\n\n{r.descripcion or ''}\n\n" + ("Parámetros: " + ", ".join(p.titulo for p in r.params) if r.params else "No requiere parámetros."))
        self.b_abrir.setEnabled(True)

    def abrir(self) -> None:
        id_ = self._sel()
        if id_:
            abrir_informe(self.ventana, self.ctx, id_)
