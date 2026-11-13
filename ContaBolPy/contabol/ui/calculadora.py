"""Calculadora de escritorio sencilla (para usar mientras se registran comprobantes)."""
from __future__ import annotations

import ast
import operator
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QGridLayout, QLineEdit, QPushButton, QVBoxLayout

from ..util import fmt

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.USub: operator.neg, ast.UAdd: operator.pos}


def evaluar(expr: str) -> float:
    """Evalúa de forma segura una expresión aritmética (+ - * / y paréntesis). Acepta coma decimal."""
    expr = expr.replace(",", ".").replace("×", "*").replace("÷", "/").replace(" ", "")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return float(n.value)
        if sys.version_info < (3, 8) and isinstance(n, ast.Num):  # Python 3.7 (Windows 7): los números son ast.Num
            return float(n.n)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("Expresión no válida")
    return ev(ast.parse(expr, mode="eval"))


class Calculadora(QDialog):
    """Calculadora flotante. 'Usar resultado' emite el valor para pegarlo en el campo activo del comprobante."""
    resultado = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calculadora")
        self.setWindowFlag(Qt.Tool, True)
        self.setFixedWidth(300)
        lay = QVBoxLayout(self)
        self.pantalla = QLineEdit()
        self.pantalla.setAlignment(Qt.AlignRight)
        self.pantalla.setStyleSheet("font-size:18pt; padding:8px;")
        self.pantalla.setPlaceholderText("0")
        lay.addWidget(self.pantalla)
        g = QGridLayout()
        teclas = ["7", "8", "9", "÷", "4", "5", "6", "×", "1", "2", "3", "-", "0", ",", "(", "+", ")", "C", "⌫", "="]
        for i, t in enumerate(teclas):
            b = QPushButton(t)
            b.setMinimumHeight(40)
            if t in "÷×-+=":
                b.setProperty("tipo", "primario")
            b.clicked.connect(lambda _=False, x=t: self.tecla(x))
            g.addWidget(b, i // 4, i % 4)
        lay.addLayout(g)
        self.usar = QPushButton("Usar resultado")
        self.usar.setProperty("tipo", "exito")
        self.usar.clicked.connect(self.emitir)
        lay.addWidget(self.usar)
        self.pantalla.returnPressed.connect(self.calcular)

    def tecla(self, t: str) -> None:
        if t == "C":
            self.pantalla.clear()
        elif t == "⌫":
            self.pantalla.setText(self.pantalla.text()[:-1])
        elif t == "=":
            self.calcular()
        else:
            self.pantalla.insert(t)

    def calcular(self) -> float | None:
        try:
            v = evaluar(self.pantalla.text())
        except Exception:  # noqa: BLE001
            self.pantalla.setStyleSheet("font-size:18pt; padding:8px; color:#B02424;")
            return None
        self.pantalla.setStyleSheet("font-size:18pt; padding:8px;")
        self.pantalla.setText(fmt(v).replace(".", ""))
        return v

    def emitir(self) -> None:
        v = self.calcular()
        if v is not None:
            self.resultado.emit(v)
