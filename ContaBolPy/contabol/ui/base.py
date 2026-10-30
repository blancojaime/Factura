"""Pantalla base: banner superior + zona de trabajo; las pantallas heredan de Pantalla."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from . import tema
from .widgets import Banner, Columna, TablaDatos, boton, confirmar, error, hbox, intentar


class Pantalla(QWidget):
    """Base de toda pestaña. Subclases definen titulo, subtitulo y construyen self.cuerpo."""
    titulo = "Pantalla"
    subtitulo = ""
    permiso = ""

    def __init__(self, ctx, ventana=None):
        super().__init__()
        self.setObjectName("lienzo")
        self.ctx = ctx
        self.ventana = ventana
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.banner = Banner(self.titulo, self.subtitulo)
        self.lay.addWidget(self.banner)
        self.cuerpo = QVBoxLayout()
        self.cuerpo.setContentsMargins(20, 14, 20, 16)
        self.cuerpo.setSpacing(10)
        self.lay.addLayout(self.cuerpo, 1)

    @property
    def tabs_id(self) -> str:
        return type(self).__name__

    def refrescar(self) -> None:
        pass

    def msg_error(self, ex):
        error(self, ex)


class ListaCRUD(Pantalla):
    """Pantalla de listado con buscador y botones de acción; las acciones reciben la fila seleccionada."""

    def __init__(self, ctx, columnas: list[Columna], cargar, acciones: list[tuple] | None = None, buscar: bool = True, ventana=None,
                 colorear=None, doble_clic=None, filtros: list | None = None):
        super().__init__(ctx, ventana)
        self._cargar = cargar
        self._colorear = colorear
        self.tabla = TablaDatos(columnas)
        self.todo: list[dict] = []
        barra = QHBoxLayout()
        barra.setSpacing(8)
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar…")
        self.buscador.setClearButtonEnabled(True)
        self.buscador.setMaximumWidth(320)
        if buscar:
            barra.addWidget(self.buscador)
        for f in filtros or []:
            barra.addWidget(f)
        barra.addStretch(1)
        self.botones: dict[str, object] = {}
        for acc in acciones or []:
            texto, fn, tipo = acc[0], acc[1], (acc[2] if len(acc) > 2 else "")
            b = boton(texto, tipo)
            b.clicked.connect(lambda _=False, f=fn: self._ejecutar(f))
            barra.addWidget(b)
            self.botones[texto] = b
        self.cuerpo.addLayout(barra)
        self.cuerpo.addWidget(self.tabla, 1)
        self.lbl_total = QLabel("")
        self.lbl_total.setObjectName("sub")
        self.cuerpo.addWidget(self.lbl_total)
        self.buscador.textChanged.connect(self._filtrar)
        if doble_clic:
            self.tabla.doble_clic.connect(lambda f: self._ejecutar(doble_clic, f))
        self.refrescar()

    def _ejecutar(self, fn, fila=None):
        fila = fila or self.tabla.fila_actual()
        ok, _ = intentar(self, fn, fila)
        if ok:
            self.refrescar()

    def refrescar(self) -> None:
        ok, filas = intentar(self, self._cargar)
        self.todo = filas if ok and filas else []
        self._filtrar()

    def _filtrar(self) -> None:
        t = self.buscador.text().strip().lower()
        filas = [f for f in self.todo if not t or any(t in str(v).lower() for v in f.values() if v is not None)]
        self.tabla.cargar(filas, self._colorear)
        self.lbl_total.setText(f"{len(filas)} registro(s)" + (f" de {len(self.todo)}" if len(filas) != len(self.todo) else ""))
