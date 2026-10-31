"""Widgets reutilizables: tablas, formularios declarativos, diálogos CRUD y manejo uniforme de errores."""
import functools
import os
import subprocess
import sys
import traceback
from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from ..reports import engine as E
from ..services.base import ServiceError


def info(parent, msg, title="SIIM 2026"):
    QMessageBox.information(parent, title, msg)


def error(parent, msg, title="No se pudo completar la operación"):
    QMessageBox.warning(parent, title, msg)


def confirm(parent, msg, title="Confirmar") -> bool:
    b = QMessageBox(QMessageBox.Question, title, msg, QMessageBox.Yes | QMessageBox.No, parent)
    b.button(QMessageBox.Yes).setText("Sí")
    b.setDefaultButton(QMessageBox.No)
    return b.exec() == QMessageBox.Yes


def guarded(fn):
    """Captura errores de negocio (mensaje claro) y técnicos (se registran, el sistema sigue funcionando)."""
    @functools.wraps(fn)
    def w(self, *a, **k):
        try:
            return fn(self, *a, **k)
        except ServiceError as e:
            error(self, str(e))
        except Exception as e:                     # error inesperado: no cerrar la aplicación
            traceback.print_exc()
            error(self, f"Error inesperado: {e}\n\nSus datos no fueron alterados parcialmente (las operaciones son atómicas). Si el problema persiste, contacte a soporte.", "Error")
    return w


def open_file(path):
    path = str(path)
    if os.name == "nt":
        os.startfile(path)                          # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def titulo(text, sub=""):
    box = QWidget()
    l = QVBoxLayout(box)
    l.setContentsMargins(0, 0, 0, 6)
    a = QLabel(text)
    a.setObjectName("titulo")
    l.addWidget(a)
    if sub:
        b = QLabel(sub)
        b.setObjectName("subtitulo")
        b.setWordWrap(True)
        l.addWidget(b)
    return box


def card():
    f = QFrame()
    f.setObjectName("card")
    return f


def btn(text, slot=None, primary=False, danger=False):
    b = QPushButton(text)
    if primary:
        b.setObjectName("primary")
    if danger:
        b.setObjectName("danger")
    if slot:
        b.clicked.connect(lambda *_: slot())
    return b


class DataTable(QTableWidget):
    """Tabla de sólo lectura con formatos (money/int/date/pct) y exportación a PDF/Excel."""
    seleccion = Signal(object)
    doble_click = Signal(object)

    def __init__(self, cols=(), parent=None):
        super().__init__(parent)
        self.cols = list(cols)
        self.rows = []
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSortingEnabled(False)
        self.set_data([])
        self.itemSelectionChanged.connect(lambda: self.seleccion.emit(self.current_row()))
        self.itemDoubleClicked.connect(lambda *_: self.doble_click.emit(self.current_row()))

    def set_cols(self, cols):
        self.cols = list(cols)
        self.setColumnCount(len(self.cols))
        self.setHorizontalHeaderLabels([c.label for c in self.cols])

    def set_data(self, rows):
        self.rows = [dict(r) if not isinstance(r, dict) else r for r in rows]
        self.setRowCount(0)
        self.setColumnCount(len(self.cols))
        self.setHorizontalHeaderLabels([c.label for c in self.cols])
        rep = E.Report("", self.cols, self.rows)
        self.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            for j, c in enumerate(self.cols):
                it = QTableWidgetItem(rep.cell(c, r))
                if c.kind in ("money", "int", "num", "pct"):
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.setItem(i, j, it)
        self.resizeColumnsToContents()
        for j, c in enumerate(self.cols):
            self.setColumnWidth(j, min(max(self.columnWidth(j) + 12, 70), 420))
        self.horizontalHeader().setStretchLastSection(True)

    def current_row(self):
        i = self.currentRow()
        return self.rows[i] if 0 <= i < len(self.rows) else None


# ---------------------------------------------------------------- formularios declarativos
class Field:
    def __init__(self, name, label, kind="text", choices=None, default=None, required=False, readonly=False, maxlen=None, lo=0, hi=1e12, decimals=2, tip=""):
        self.name, self.label, self.kind, self.choices, self.default = name, label, kind, choices, default
        self.required, self.readonly, self.maxlen, self.lo, self.hi, self.decimals, self.tip = required, readonly, maxlen, lo, hi, decimals, tip


class FormPanel(QWidget):
    """Construye un formulario a partir de una lista de Field."""

    def __init__(self, fields, parent=None, columns=1):
        super().__init__(parent)
        self.fields = fields
        self.w = {}
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        forms = [QFormLayout() for _ in range(columns)]
        for f in forms:
            f.setLabelAlignment(Qt.AlignRight)
            f.setHorizontalSpacing(10)
            f.setVerticalSpacing(8)
        per = -(-len(fields) // columns)
        for i, f in enumerate(fields):
            wd = self._make(f)
            self.w[f.name] = wd
            lab = f.label + (" *" if f.required else "")
            forms[min(i // per, columns - 1)].addRow(lab, wd)
        for f in forms:
            box = QWidget()
            box.setLayout(f)
            outer.addWidget(box, 1)

    def _make(self, f):
        k = f.kind
        if k == "text":
            w = QLineEdit(str(f.default or ""))
            if f.maxlen:
                w.setMaxLength(f.maxlen)
        elif k == "area":
            w = QTextEdit()
            w.setFixedHeight(64)
        elif k == "int":
            w = QSpinBox(); w.setRange(int(f.lo), int(min(f.hi, 2_000_000_000))); w.setValue(int(f.default or 0)); w.setGroupSeparatorShown(False)
        elif k == "float":
            w = QDoubleSpinBox(); w.setDecimals(f.decimals); w.setRange(f.lo, f.hi); w.setValue(float(f.default or 0)); w.setGroupSeparatorShown(True)
        elif k == "date":
            w = QDateEdit(); w.setCalendarPopup(True); w.setDisplayFormat("dd/MM/yyyy"); w.setDate(QDate.currentDate() if f.default in (None, "hoy") else QDate.fromString(str(f.default), "yyyy-MM-dd"))
        elif k == "date?":                         # fecha opcional
            w = QDateEdit(); w.setCalendarPopup(True); w.setDisplayFormat("dd/MM/yyyy"); w.setSpecialValueText("—"); w.setMinimumDate(QDate(1900, 1, 1)); w.setDate(QDate(1900, 1, 1))
        elif k == "choice":
            w = QComboBox()
            for c in f.choices or []:
                if isinstance(c, (tuple, list)):
                    w.addItem(str(c[1]), c[0])
                else:
                    w.addItem(str(c), c)
            if f.default is not None:
                i = w.findData(f.default)
                w.setCurrentIndex(max(i, 0))
        elif k == "bool":
            w = QCheckBox(); w.setChecked(bool(f.default))
        else:
            raise ValueError(k)
        if f.readonly and hasattr(w, "setReadOnly"):
            w.setReadOnly(True)
        if f.tip:
            w.setToolTip(f.tip)
        return w

    def set_choices(self, name, choices, keep=True):
        w = self.w[name]
        cur = w.currentData() if keep else None
        w.blockSignals(True)
        w.clear()
        for c in choices:
            if isinstance(c, (tuple, list)):
                w.addItem(str(c[1]), c[0])
            else:
                w.addItem(str(c), c)
        i = w.findData(cur) if cur is not None else -1
        w.setCurrentIndex(i if i >= 0 else 0)
        w.blockSignals(False)

    def get(self, name):
        w = self.w[name]
        f = next(x for x in self.fields if x.name == name)
        if isinstance(w, QLineEdit):
            return w.text().strip() or None
        if isinstance(w, QTextEdit):
            return w.toPlainText().strip() or None
        if isinstance(w, QSpinBox):
            return int(w.value())
        if isinstance(w, QDoubleSpinBox):
            return float(w.value())
        if isinstance(w, QDateEdit):
            if f.kind == "date?" and w.date() == QDate(1900, 1, 1):
                return None
            return w.date().toString("yyyy-MM-dd")
        if isinstance(w, QComboBox):
            return w.currentData()
        if isinstance(w, QCheckBox):
            return 1 if w.isChecked() else 0

    def values(self):
        return {f.name: self.get(f.name) for f in self.fields}

    def set(self, name, v):
        w = self.w[name]
        f = next(x for x in self.fields if x.name == name)
        if isinstance(w, QLineEdit):
            w.setText("" if v is None else str(v))
        elif isinstance(w, QTextEdit):
            w.setPlainText("" if v is None else str(v))
        elif isinstance(w, QSpinBox):
            w.setValue(int(v or 0))
        elif isinstance(w, QDoubleSpinBox):
            w.setValue(float(v or 0))
        elif isinstance(w, QDateEdit):
            if v:
                w.setDate(QDate.fromString(str(v)[:10], "yyyy-MM-dd"))
            else:
                w.setDate(QDate(1900, 1, 1) if f.kind == "date?" else QDate.currentDate())
        elif isinstance(w, QComboBox):
            i = w.findData(v)
            if i < 0 and v is not None:
                w.addItem(str(v), v); i = w.count() - 1
            w.setCurrentIndex(max(i, 0))
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(v))

    def load(self, d):
        for f in self.fields:
            if f.name in d.keys():
                self.set(f.name, d[f.name])

    def validate(self):
        miss = [f.label for f in self.fields if f.required and self.get(f.name) in (None, "")]
        if miss:
            raise ServiceError("Complete los campos obligatorios: " + ", ".join(miss))


class CrudDialog(QDialog):
    def __init__(self, title, fields, values=None, parent=None, columns=1, width=520):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        lay = QVBoxLayout(self)
        self.form = FormPanel(fields, columns=columns)
        lay.addWidget(self.form)
        if values:
            self.form.load(values)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Aceptar")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.button(QDialogButtonBox.Ok).setObjectName("primary")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _ok(self):
        try:
            self.form.validate()
        except ServiceError as e:
            error(self, str(e))
            return
        self.accept()

    @staticmethod
    def ask(title, fields, values=None, parent=None, **k):
        d = CrudDialog(title, fields, values, parent, **k)
        return d.form.values() if d.exec() == QDialog.Accepted else None


class ExportBar(QWidget):
    """Botones Excel/PDF para un Report generado por una función."""

    def __init__(self, get_report, ctx_get, parent=None):
        super().__init__(parent)
        self.get_report, self.ctx_get = get_report, ctx_get
        l = QHBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.addStretch(1)
        l.addWidget(btn("Exportar a Excel", self.xlsx))
        l.addWidget(btn("Ver / imprimir PDF", self.pdf, primary=True))

    @guarded
    def pdf(self, *_):
        from ..core.paths import reports_dir
        r = self.get_report()
        ctx = self.ctx_get()
        p = reports_dir() / f"{r.code or 'reporte'}_{date.today():%Y%m%d}_{os.getpid()}.pdf"
        E.to_pdf(r, p, ctx.db.param("municipio", ""), ctx.user)
        open_file(p)

    @guarded
    def xlsx(self, *_):
        r = self.get_report()
        ctx = self.ctx_get()
        fn, _ = QFileDialog.getSaveFileName(self, "Guardar Excel", f"{r.code or 'reporte'}_{date.today():%Y%m%d}.xlsx", "Excel (*.xlsx)")
        if fn:
            E.to_xlsx(r, fn, ctx.db.param("municipio", ""), ctx.user)
            if confirm(self, "Archivo guardado. ¿Abrirlo ahora?"):
                open_file(fn)
