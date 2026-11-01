"""Activación de la licencia (usuario) y emisión de códigos de activación (proveedor)."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout

from .. import licencia
from . import tema
from .widgets import CampoFecha, aviso, boton, hbox, info


def _caja_codigo(texto: str) -> QLineEdit:
    e = QLineEdit(texto)
    e.setReadOnly(True)
    e.setStyleSheet("font-family: Consolas, monospace; font-size: 13pt; font-weight:600; letter-spacing:1px;")
    return e


class ActivacionDialog(QDialog):
    """Pantalla de activación: muestra el código de solicitud y permite pegar el código de activación recibido."""

    def __init__(self, sis, parent=None, al_inicio: bool = False):
        super().__init__(parent)
        self.sis, self.al_inicio = sis, al_inicio
        self.continuar_prueba = False
        self.setWindowTitle("CONTA JB - Activación de la licencia")
        self.setWindowIcon(tema.icono_app())
        self.setMinimumWidth(620)
        self.est = licencia.estado(sis)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 20)
        lay.setSpacing(8)
        h = QLabel("Activación de CONTA JB")
        h.setObjectName("h1")
        lay.addWidget(h)
        self.l_estado = QLabel("")
        self.l_estado.setWordWrap(True)
        lay.addWidget(self.l_estado)
        pasos = QLabel("<b>Paso 1.</b> Copie su <b>código de solicitud</b> y envíelo a su proveedor (correo o WhatsApp).<br>"
                       "<b>Paso 2.</b> Pegue abajo el <b>código de activación</b> que reciba y pulse <b>Activar</b>.")
        pasos.setWordWrap(True)
        lay.addWidget(pasos)
        lay.addWidget(QLabel("Código de solicitud de este equipo:"))
        self.c_sol = _caja_codigo(self.est["solicitud"])
        b_copiar = boton("Copiar", "", 90)
        b_copiar.clicked.connect(self._copiar)
        lay.addLayout(hbox(self.c_sol, b_copiar))
        lay.addWidget(QLabel("Código de activación recibido:"))
        self.c_cod = QPlainTextEdit()
        self.c_cod.setPlaceholderText("Pegue aquí el código de activación…")
        self.c_cod.setFixedHeight(84)
        lay.addWidget(self.c_cod)
        self.err = QLabel("")
        self.err.setWordWrap(True)
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        lay.addWidget(self.err)
        self.b_act = boton("Activar", "primario", 130)
        self.b_prueba = boton("Continuar en modo de prueba", "", 210)
        self.b_salir = boton("Salir" if al_inicio else "Cerrar", "", 100)
        lay.addLayout(hbox(None, self.b_salir, self.b_prueba, self.b_act))
        self.b_act.clicked.connect(self.activar)
        self.b_prueba.clicked.connect(self._prueba)
        self.b_salir.clicked.connect(self.reject)
        self._estado()

    def _estado(self):
        self.est = licencia.estado(self.sis)
        e = self.est
        color = {"activada": "#287846", "prueba": "#B7791F"}.get(e["modo"], tema.ROJO)
        self.l_estado.setText(f"<span style='color:{color}; font-weight:600;'>{e['mensaje']}</span>")
        self.b_prueba.setVisible(self.al_inicio and e["modo"] == "prueba")
        self.b_act.setEnabled(e["modo"] != "bloqueada")

    def _copiar(self):
        QApplication.clipboard().setText(self.c_sol.text())
        info(self, "Código de solicitud copiado. Péguelo en el mensaje a su proveedor.")

    def activar(self):
        try:
            licencia.activar(self.sis, self.c_cod.toPlainText())
        except ValueError as ex:
            self.err.setText(str(ex))
            return
        self.err.setText("")
        self._estado()
        info(self, "¡CONTA JB quedó activado! " + self.est["mensaje"] + ".")
        self.accept()

    def _prueba(self):
        self.continuar_prueba = True
        self.accept()


class EmisionDialog(QDialog):
    """Herramienta del PROVEEDOR: genera el código de activación a partir de un código de solicitud, con su clave privada."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Emitir código de activación (proveedor)")
        self.setWindowIcon(tema.icono_app())
        self.setMinimumWidth(640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 20)
        lay.setSpacing(8)
        h = QLabel("Emitir código de activación")
        h.setObjectName("h1")
        lay.addWidget(h)
        aviso_ = QLabel("Solo para el proveedor: requiere el archivo de <b>clave privada</b> (clave_privada_contajb.pem). Guárdelo fuera de las computadoras de los clientes.")
        aviso_.setWordWrap(True)
        lay.addWidget(aviso_)
        self.e_clave = QLineEdit()
        self.e_clave.setPlaceholderText("Archivo de clave privada (.pem)")
        b_ex = boton("Examinar…", "", 110)
        b_ex.clicked.connect(self._examinar)
        lay.addLayout(hbox(self.e_clave, b_ex))
        self.e_sol = QLineEdit()
        self.e_sol.setPlaceholderText("Código de solicitud del cliente: JB-XXXX-XXXX-XXXX-XXXX-XXXX")
        lay.addWidget(QLabel("Código de solicitud del cliente"))
        lay.addWidget(self.e_sol)
        self.perpetua = QCheckBox("Licencia perpetua (sin vencimiento)")
        self.perpetua.setChecked(True)
        self.vence = CampoFecha(date.today().replace(year=date.today().year + 1), date.today(), date(2099, 12, 31))
        self.vence.setEnabled(False)
        self.perpetua.toggled.connect(lambda v: self.vence.setEnabled(not v))
        lay.addLayout(hbox(self.perpetua, QLabel("Vence el"), self.vence, None))
        self.b_gen = boton("Generar código", "primario", 150)
        self.b_gen.clicked.connect(self.generar)
        lay.addWidget(self.b_gen)
        self.salida = QPlainTextEdit()
        self.salida.setReadOnly(True)
        self.salida.setFixedHeight(90)
        self.salida.setStyleSheet("font-family: Consolas, monospace;")
        lay.addWidget(self.salida)
        self.err = QLabel("")
        self.err.setWordWrap(True)
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        lay.addWidget(self.err)
        b_cp = boton("Copiar código", "", 130)
        b_ce = boton("Cerrar", "", 100)
        b_cp.clicked.connect(lambda: QApplication.clipboard().setText(self.salida.toPlainText()))
        b_ce.clicked.connect(self.reject)
        lay.addLayout(hbox(None, b_ce, b_cp))

    def _examinar(self):
        r, _ = QFileDialog.getOpenFileName(self, "Clave privada", "", "Clave PEM (*.pem);;Todos (*.*)")
        if r:
            self.e_clave.setText(r)

    def generar(self):
        try:
            with open(self.e_clave.text().strip(), "rb") as f:
                pem = f.read()
            self.salida.setPlainText(licencia.emitir(pem, self.e_sol.text(), None if self.perpetua.isChecked() else self.vence.fecha()))
            self.err.setText("")
        except (OSError, ValueError) as ex:
            self.salida.clear()
            self.err.setText(f"No se pudo generar: {ex}")
