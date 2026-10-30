"""Formulario dinámico a partir de una especificación de campos."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QFormLayout, QGridLayout, QLabel, QLineEdit, QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget

from . import tema
from .widgets import CampoFecha, CampoImporte, Combo, boton, error, hbox


@dataclass
class Campo:
    clave: str
    etiqueta: str
    tipo: str = "txt"        # txt, int, money, num, date, combo, check, memo, ro
    obligatorio: bool = False
    opciones: list | Callable | None = None   # para combo: [(valor, texto)]
    defecto: Any = None
    ancho: int = 1           # 1 = media fila, 2 = fila completa
    maximo: int | None = None
    decimales: int = 2
    vacio: str | None = None


class FormDialog(QDialog):
    """Cuadro de diálogo modal con campos en dos columnas. guardar(valores) se ejecuta al aceptar; si lanza error se muestra y no se cierra."""

    def __init__(self, titulo: str, campos: list[Campo], valores: dict | None = None, guardar: Callable[[dict], Any] | None = None,
                 ayuda: str = "", parent=None, ancho: int = 720, texto_ok: str = "Guardar"):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(ancho)
        self.campos = campos
        self.w: dict[str, QWidget] = {}
        self._guardar = guardar
        self.resultado = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)
        h = QLabel(titulo)
        h.setObjectName("h1")
        lay.addWidget(h)
        if ayuda:
            a = QLabel(ayuda)
            a.setObjectName("sub")
            a.setWordWrap(True)
            lay.addWidget(a)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        col, fila = 0, 0
        v = valores or {}
        for c in campos:
            w = self._crear(c, v.get(c.clave, c.defecto))
            self.w[c.clave] = w
            caja = QVBoxLayout()
            caja.setSpacing(3)
            et = QLabel(c.etiqueta + (" *" if c.obligatorio else ""))
            et.setObjectName("etq")
            if c.tipo != "check":
                caja.addWidget(et)
            caja.addWidget(w)
            cont = QWidget()
            cont.setLayout(caja)
            caja.setContentsMargins(0, 0, 0, 0)
            if c.ancho >= 2 or c.tipo == "memo":
                if col == 1:
                    fila += 1
                    col = 0
                grid.addWidget(cont, fila, 0, 1, 2)
                fila += 1
                col = 0
            else:
                grid.addWidget(cont, fila, col)
                col += 1
                if col == 2:
                    col, fila = 0, fila + 1
        lay.addLayout(grid)
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(f"color:{tema.ROJO};")
        self.lbl_error.setWordWrap(True)
        lay.addWidget(self.lbl_error)
        self.b_ok = boton(texto_ok, "primario", 110)
        self.b_cancel = boton("Cancelar", "", 100)
        self.b_ok.setDefault(True)
        lay.addLayout(hbox(None, self.b_cancel, self.b_ok))
        self.b_ok.clicked.connect(self._aceptar)
        self.b_cancel.clicked.connect(self.reject)

    def _crear(self, c: Campo, valor) -> QWidget:
        if c.tipo == "money" or c.tipo == "num":
            w = CampoImporte(float(valor or 0), c.decimales)
        elif c.tipo == "int":
            w = QSpinBox()
            w.setRange(-10**9, 10**9)
            w.setValue(int(valor or 0))
        elif c.tipo == "date":
            w = CampoFecha(valor)
        elif c.tipo == "combo":
            w = Combo()
            ops = c.opciones() if callable(c.opciones) else (c.opciones or [])
            w.cargar(ops, c.vacio)
            if valor is not None:
                w.set_valor(valor)
        elif c.tipo == "check":
            w = QCheckBox(c.etiqueta)
            w.setChecked(bool(valor))
        elif c.tipo == "memo":
            w = QPlainTextEdit(str(valor or ""))
            w.setFixedHeight(70)
        elif c.tipo == "ro":
            w = QLineEdit(str(valor or ""))
            w.setReadOnly(True)
        else:
            w = QLineEdit(str(valor if valor is not None else ""))
            if c.maximo:
                w.setMaxLength(c.maximo)
        return w

    def valor(self, clave: str):
        c = next(x for x in self.campos if x.clave == clave)
        w = self.w[clave]
        if isinstance(w, CampoImporte):
            return w.valor()
        if isinstance(w, QSpinBox):
            return w.value()
        if isinstance(w, CampoFecha):
            return w.fecha()
        if isinstance(w, Combo):
            return w.valor()
        if isinstance(w, QCheckBox):
            return w.isChecked()
        if isinstance(w, QPlainTextEdit):
            return w.toPlainText().strip()
        return w.text().strip()

    def valores(self) -> dict:
        return {c.clave: self.valor(c.clave) for c in self.campos}

    def _aceptar(self) -> None:
        v = self.valores()
        for c in self.campos:
            if c.obligatorio and c.tipo != "check" and (v[c.clave] in (None, "", 0) and c.tipo not in ("money", "num", "int")):
                self.lbl_error.setText(f"El campo «{c.etiqueta}» es obligatorio.")
                self.w[c.clave].setFocus()
                return
        try:
            if self._guardar:
                self.resultado = self._guardar(v)
        except Exception as ex:  # noqa: BLE001
            from ..sistema import ErrorNegocio
            if isinstance(ex, (ErrorNegocio, ValueError)):
                self.lbl_error.setText(str(ex))
            else:
                error(self, ex)
            return
        self.accept()
