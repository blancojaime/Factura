"""Componentes reutilizables: tabla de datos, campos validados, tarjetas, gráfico y mensajes."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QLocale, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDoubleValidator, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..sistema import ErrorNegocio
from ..util import fmt, parse_num, to_date
from . import tema


# ------------------------------------------------------------------- mensajes
def _caja(parent, icono_, titulo, texto, botones=QMessageBox.Ok):
    m = QMessageBox(parent)
    m.setIcon(icono_)
    m.setWindowTitle(titulo)
    m.setText(texto)
    m.setStandardButtons(botones)
    return m


def info(parent, texto: str, titulo: str = "ContaBol") -> None:
    _caja(parent, QMessageBox.Information, titulo, texto).exec()


def aviso(parent, texto: str, titulo: str = "Atención") -> None:
    _caja(parent, QMessageBox.Warning, titulo, texto).exec()


def error(parent, ex: Exception | str) -> None:
    if isinstance(ex, ErrorNegocio) or isinstance(ex, ValueError):
        aviso(parent, str(ex), "No se pudo completar la operación")
    else:
        import logging
        logging.getLogger("contabol").exception("Error inesperado", exc_info=ex if isinstance(ex, BaseException) else None)
        _caja(parent, QMessageBox.Critical, "Error inesperado", f"Ocurrió un error inesperado:\n\n{ex}\n\nEl detalle quedó registrado en el archivo de registro.").exec()


def confirmar(parent, texto: str, titulo: str = "Confirmar", peligro: bool = False) -> bool:
    m = _caja(parent, QMessageBox.Warning if peligro else QMessageBox.Question, titulo, texto, QMessageBox.Yes | QMessageBox.No)
    m.button(QMessageBox.Yes).setText("Sí")
    m.button(QMessageBox.No).setText("No")
    m.setDefaultButton(QMessageBox.No if peligro else QMessageBox.Yes)
    return m.exec() == QMessageBox.Yes


def intentar(parent, fn, *a, **k):
    """Ejecuta fn; muestra errores de negocio como avisos. Devuelve (ok, resultado)."""
    try:
        return True, fn(*a, **k)
    except Exception as ex:  # noqa: BLE001
        error(parent, ex)
        return False, None


# ---------------------------------------------------------------------- botones
def boton(texto: str, tipo: str = "", ancho: int | None = None, icono_=None) -> QPushButton:
    b = QPushButton(texto)
    if tipo:
        b.setProperty("tipo", tipo)
    if ancho:
        b.setMinimumWidth(ancho)
    if icono_:
        b.setIcon(icono_)
    b.setCursor(Qt.PointingHandCursor)
    return b


# ----------------------------------------------------------------------- campos
class CampoImporte(QLineEdit):
    """Importe con formato boliviano (1.234,56). Acepta coma o punto al escribir."""
    cambiado = Signal(float)

    def __init__(self, valor: float = 0.0, decimales: int = 2, parent=None):
        super().__init__(parent)
        self.decimales = decimales
        self.setAlignment(Qt.AlignRight)
        v = QDoubleValidator(-1e12, 1e12, 6)
        v.setNotation(QDoubleValidator.StandardNotation)
        self.setValidator(None)
        self.set_valor(valor)
        self.editingFinished.connect(self._normalizar)

    def valor(self) -> float:
        return parse_num(self.text())

    def set_valor(self, v: float) -> None:
        self.setText(fmt(v, self.decimales))

    def _normalizar(self) -> None:
        self.set_valor(self.valor())
        self.cambiado.emit(self.valor())

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.selectAll()


class CampoFecha(QDateEdit):
    def __init__(self, fecha=None, minimo=None, maximo=None, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("dd/MM/yyyy")
        self.setCalendarPopup(True)
        self.setLocale(QLocale(QLocale.Spanish, QLocale.Bolivia))
        if minimo:
            self.setMinimumDate(QDate(minimo.year, minimo.month, minimo.day))
        if maximo:
            self.setMaximumDate(QDate(maximo.year, maximo.month, maximo.day))
        self.set_fecha(fecha or date.today())

    def fecha(self) -> date:
        d = self.date()
        return date(d.year(), d.month(), d.day())

    def set_fecha(self, f) -> None:
        f = to_date(f) or date.today()
        self.setDate(QDate(f.year, f.month, f.day))


class Combo(QComboBox):
    """Combo con pares (valor, texto)."""

    def __init__(self, opciones=None, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.setMinimumWidth(140)
        if opciones:
            self.cargar(opciones)

    def cargar(self, opciones, vacio: str | None = None) -> None:
        self.clear()
        if vacio is not None:
            self.addItem(vacio, None)
        for v, t in opciones:
            self.addItem(t, v)

    def valor(self):
        return self.currentData()

    def set_valor(self, v) -> None:
        i = self.findData(v)
        self.setCurrentIndex(i if i >= 0 else 0)


# ------------------------------------------------------------------ cabeceras
class Banner(QFrame):
    """Cabecera de pantalla: título, subtítulo y zona de botones a la derecha."""

    def __init__(self, titulo: str, subtitulo: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("banner")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 14, 22, 12)
        col = QVBoxLayout()
        col.setSpacing(1)
        self.h1 = QLabel(titulo)
        self.h1.setObjectName("h1")
        self.sub = QLabel(subtitulo)
        self.sub.setObjectName("sub")
        self.sub.setWordWrap(True)
        col.addWidget(self.h1)
        if subtitulo:
            col.addWidget(self.sub)
        lay.addLayout(col, 1)
        self.acciones = QHBoxLayout()
        self.acciones.setSpacing(8)
        lay.addLayout(self.acciones)

    def agregar(self, w: QWidget) -> QWidget:
        self.acciones.addWidget(w)
        return w


class Tarjeta(QFrame):
    def __init__(self, titulo: str, valor: str, color: str = tema.AZUL, detalle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("tarjeta")
        self.setMinimumHeight(92)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        t = QLabel(titulo)
        t.setObjectName("kpit")
        self.v = QLabel(valor)
        self.v.setObjectName("kpiv")
        self.v.setStyleSheet(f"color:{color};")
        lay.addWidget(t)
        lay.addWidget(self.v)
        if detalle:
            d = QLabel(detalle)
            d.setObjectName("sub")
            lay.addWidget(d)


class GraficoBarras(QWidget):
    """Gráfico de barras agrupadas (dos series) dibujado con QPainter."""

    def __init__(self, etiquetas, serie1, serie2, nombre1="Ventas", nombre2="Compras", parent=None):
        super().__init__(parent)
        self.et, self.s1, self.s2, self.n1, self.n2 = etiquetas, serie1, serie2, nombre1, nombre2
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        izq, abajo, arriba = 56, 34, 28
        mx = max(max(self.s1 + self.s2, default=0), 1)
        paso = self._paso(mx)
        tope = paso * (int(mx / paso) + 1)
        p.setFont(tema.fuente(8))
        p.setPen(QPen(QColor(tema.BORDE)))
        n = int(tope / paso)
        for i in range(n + 1):
            y = h - abajo - (h - abajo - arriba) * i / n
            p.drawLine(izq, int(y), w - 8, int(y))
            p.setPen(QPen(QColor(tema.GRIS)))
            p.drawText(QRectF(0, y - 9, izq - 6, 18), Qt.AlignRight | Qt.AlignVCenter, self._abrev(paso * i))
            p.setPen(QPen(QColor(tema.BORDE)))
        k = len(self.et)
        ancho = (w - izq - 12) / max(k, 1)
        for i, e in enumerate(self.et):
            x0 = izq + i * ancho
            for j, (serie, color) in enumerate(((self.s1, tema.AZUL), (self.s2, "#7FB2F0"))):
                v = serie[i] if i < len(serie) else 0
                alto = (h - abajo - arriba) * v / tope
                bw = ancho * 0.28
                r = QRectF(x0 + ancho * 0.18 + j * (bw + 2), h - abajo - alto, bw, alto)
                p.fillRect(r, QColor(color))
            p.setPen(QPen(QColor(tema.GRIS)))
            p.drawText(QRectF(x0, h - abajo + 4, ancho, 18), Qt.AlignCenter, e)
        p.setPen(Qt.NoPen)
        for j, (n_, c) in enumerate(((self.n1, tema.AZUL), (self.n2, "#7FB2F0"))):
            p.fillRect(QRectF(izq + j * 90, 8, 10, 10), QColor(c))
            p.setPen(QPen(QColor(tema.GRIS)))
            p.drawText(QRectF(izq + j * 90 + 14, 3, 70, 20), Qt.AlignLeft | Qt.AlignVCenter, n_)
            p.setPen(Qt.NoPen)

    @staticmethod
    def _paso(mx: float) -> float:
        import math
        base = 10 ** math.floor(math.log10(mx / 4 if mx > 0 else 1))
        for m in (1, 2, 2.5, 5, 10):
            if base * m * 4 >= mx:
                return base * m
        return base * 10

    @staticmethod
    def _abrev(v: float) -> str:
        if v >= 1e6:
            return f"{v / 1e6:.1f}M"
        if v >= 1e3:
            return f"{v / 1e3:.0f}k"
        return f"{v:.0f}"


# ----------------------------------------------------------------------- tabla
class Columna:
    def __init__(self, clave: str, titulo: str, ancho: int = 100, tipo: str = "txt", decimales: int = 2, estirar: bool = False):
        self.clave, self.titulo, self.ancho, self.tipo, self.decimales, self.estirar = clave, titulo, ancho, tipo, decimales, estirar


class TablaDatos(QTableWidget):
    """Tabla de solo lectura con formato por tipo de columna (importes a la derecha, fechas, sí/no)."""
    doble_clic = Signal(dict)
    seleccion = Signal(object)

    def __init__(self, columnas: list[Columna], parent=None):
        super().__init__(0, len(columnas), parent)
        self.columnas = columnas
        self.filas: list[dict] = []
        self.setHorizontalHeaderLabels([c.titulo for c in columnas])
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(30)
        self.setShowGrid(False)
        self.setWordWrap(False)
        h = self.horizontalHeader()
        h.setHighlightSections(False)
        h.setMinimumSectionSize(40)
        for i, c in enumerate(columnas):
            if c.estirar:
                h.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                h.setSectionResizeMode(i, QHeaderView.Interactive)
                self.setColumnWidth(i, c.ancho)
        self.itemSelectionChanged.connect(lambda: self.seleccion.emit(self.fila_actual()))
        self.cellDoubleClicked.connect(lambda r, c: self.doble_clic.emit(self.filas[r]) if 0 <= r < len(self.filas) else None)

    @staticmethod
    def _texto(v, c: Columna) -> str:
        if v is None or v == "":
            return ""
        if c.tipo in ("money", "num"):
            return fmt(v, c.decimales)
        if c.tipo == "int":
            return f"{int(v):,}".replace(",", ".")
        if c.tipo == "pct":
            return fmt(v, 2) + "%"
        if c.tipo == "date":
            d = to_date(v)
            return d.strftime("%d/%m/%Y") if d else str(v)
        if c.tipo == "bool":
            return "Sí" if v else "No"
        return str(v)

    def cargar(self, filas: list[dict], colorear=None) -> None:
        self.setUpdatesEnabled(False)
        self.filas = filas
        self.setRowCount(len(filas))
        for r, f in enumerate(filas):
            for i, c in enumerate(self.columnas):
                it = QTableWidgetItem(self._texto(f.get(c.clave), c))
                if c.tipo in ("money", "num", "int", "pct"):
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    v = f.get(c.clave)
                    if c.tipo == "money" and isinstance(v, (int, float)) and v < 0:
                        it.setForeground(QColor(tema.ROJO))
                elif c.tipo in ("date", "bool"):
                    it.setTextAlignment(Qt.AlignCenter)
                if colorear:
                    col = colorear(f, c)
                    if col:
                        it.setForeground(QColor(col))
                self.setItem(r, i, it)
        self.setUpdatesEnabled(True)

    def fila_actual(self) -> dict | None:
        r = self.currentRow()
        return self.filas[r] if 0 <= r < len(self.filas) else None


def hbox(*ws, espacio: int = 8, margen=(0, 0, 0, 0), estirar_ultimo: bool = False) -> QHBoxLayout:
    l = QHBoxLayout()
    l.setSpacing(espacio)
    l.setContentsMargins(*margen)
    for w in ws:
        if w is None:
            l.addStretch(1)
        else:
            l.addWidget(w)
    return l


def etiqueta(texto: str, nombre: str = "etq") -> QLabel:
    l = QLabel(texto)
    l.setObjectName(nombre)
    return l
