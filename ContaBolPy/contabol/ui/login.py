"""Ingreso al sistema, cambio de contraseña y selección de empresa y gestión."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget, QCheckBox, QSpinBox

from .. import APP_NAME, __version__
from ..sistema import ErrorNegocio, Sistema
from . import tema
from .formularios import Campo, FormDialog
from .widgets import Combo, aviso, boton, confirmar, error, etiqueta, hbox, info, intentar


class LoginDialog(QDialog):
    def __init__(self, sis: Sistema, parent=None):
        super().__init__(parent)
        self.sis = sis
        self.usuario: dict | None = None
        self.setWindowTitle("ContaBol - Ingreso al sistema")
        self.setFixedWidth(470)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 28, 34, 26)
        lay.setSpacing(6)
        fila = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(tema.logo_pixmap(58))
        tit = QVBoxLayout()
        t1 = QLabel("ContaBol")
        t1.setStyleSheet(f"font-size:24pt; font-weight:600; color:{tema.AZUL};")
        t2 = QLabel("Sistema Contable Integrado")
        t2.setObjectName("sub")
        tit.addWidget(t1)
        tit.addWidget(t2)
        fila.addWidget(logo)
        fila.addSpacing(12)
        fila.addLayout(tit, 1)
        lay.addLayout(fila)
        lay.addSpacing(16)
        lay.addWidget(etiqueta("Usuario"))
        self.u = QLineEdit()
        self.u.setPlaceholderText("Ingrese su usuario")
        lay.addWidget(self.u)
        lay.addWidget(etiqueta("Contraseña"))
        self.c = QLineEdit()
        self.c.setEchoMode(QLineEdit.Password)
        self.c.setPlaceholderText("Ingrese su contraseña")
        lay.addWidget(self.c)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)
        lay.addSpacing(8)
        self.b = boton("Ingresar", "primario")
        self.b.setMinimumHeight(38)
        self.b.setDefault(True)
        lay.addWidget(self.b)
        pie = QLabel(f"Versión {__version__}  ·  Normativa boliviana vigente")
        pie.setObjectName("sub")
        pie.setAlignment(Qt.AlignCenter)
        lay.addSpacing(6)
        lay.addWidget(pie)
        self.b.clicked.connect(self.entrar)
        self.u.returnPressed.connect(lambda: self.c.setFocus())
        self.c.returnPressed.connect(self.entrar)

    def entrar(self) -> None:
        try:
            self.usuario = self.sis.autenticar(self.u.text(), self.c.text())
        except Exception as ex:  # noqa: BLE001
            self.err.setText(str(ex))
            self.c.clear()
            self.c.setFocus()
            return
        self.accept()


class CambioClaveDialog(QDialog):
    def __init__(self, sis: Sistema, usuario: dict, obligatorio: bool = False, parent=None):
        super().__init__(parent)
        self.sis, self.usuario = sis, usuario
        self.setWindowTitle("Cambiar contraseña")
        self.setFixedWidth(430)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 20)
        h = QLabel("Cambiar contraseña")
        h.setObjectName("h1")
        lay.addWidget(h)
        if obligatorio:
            a = QLabel("Es su primer ingreso o se restableció su contraseña: debe elegir una nueva (mínimo 6 caracteres).")
            a.setObjectName("sub")
            a.setWordWrap(True)
            lay.addWidget(a)
        self.n1, self.n2 = QLineEdit(), QLineEdit()
        for e in (self.n1, self.n2):
            e.setEchoMode(QLineEdit.Password)
        lay.addWidget(etiqueta("Nueva contraseña"))
        lay.addWidget(self.n1)
        lay.addWidget(etiqueta("Repita la nueva contraseña"))
        lay.addWidget(self.n2)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)
        ok, cancel = boton("Guardar", "primario", 100), boton("Cancelar", "", 100)
        lay.addLayout(hbox(None, cancel, ok))
        ok.clicked.connect(self.guardar)
        cancel.clicked.connect(self.reject)
        if obligatorio:
            cancel.setEnabled(False)

    def guardar(self) -> None:
        if self.n1.text() != self.n2.text():
            self.err.setText("Las contraseñas no coinciden.")
            return
        try:
            self.sis.cambiar_clave(self.usuario["id"], self.n1.text())
        except Exception as ex:  # noqa: BLE001
            self.err.setText(str(ex))
            return
        self.accept()


def dialogo_nueva_empresa(sis: Sistema, usuario: dict, parent=None) -> tuple[int, int] | None:
    campos = [
        Campo("codigo", "Código (corto)", "txt", True, maximo=12, defecto="MIEMPRESA"), Campo("razon_social", "Razón social", "txt", True, ancho=2),
        Campo("nombre_comercial", "Nombre comercial"), Campo("nit", "NIT"), Campo("direccion", "Dirección", ancho=2), Campo("ciudad", "Ciudad"),
        Campo("telefono", "Teléfono"), Campo("actividad", "Actividad económica", ancho=2), Campo("rep_legal", "Representante legal"),
        Campo("anio", "Año de la primera gestión", "int", True, defecto=__import__("datetime").date.today().year),
        Campo("mensual", "Numerar comprobantes por tipo y mes (recomendado)", "check", defecto=True, ancho=2)]
    res: dict = {}

    def guardar(v):
        res["ids"] = sis.crear_empresa(v, int(v["anio"]), usuario, bool(v["mensual"]))

    dlg = FormDialog("Nueva empresa", campos, None, guardar, "Se creará la empresa con su primera gestión y el plan de cuentas boliviano base. Podrá ajustarlo luego.", parent)
    if dlg.exec() == QDialog.Accepted:
        return res.get("ids")
    return None


class SelectorEmpresa(QDialog):
    """Lista de empresas y gestiones disponibles para el usuario. Devuelve (empresa_id, gestion_id)."""

    def __init__(self, sis: Sistema, usuario: dict, parent=None):
        super().__init__(parent)
        self.sis, self.usuario = sis, usuario
        self.seleccion: tuple[int, int] | None = None
        self.setWindowTitle("Seleccionar empresa y gestión")
        self.setMinimumSize(720, 480)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        h = QLabel("Seleccione la empresa y la gestión de trabajo")
        h.setObjectName("h1")
        lay.addWidget(h)
        s = QLabel(f"Usuario: {usuario['nombre']}")
        s.setObjectName("sub")
        lay.addWidget(s)
        cuerpo = QHBoxLayout()
        self.l_emp = QListWidget()
        self.l_ges = QListWidget()
        for l in (self.l_emp, self.l_ges):
            l.setStyleSheet("QListWidget::item { padding: 10px; } QListWidget::item:selected { background:%s; color:%s; }" % (tema.AZUL_CLARO, tema.AZUL))
        c1, c2 = QVBoxLayout(), QVBoxLayout()
        c1.addWidget(etiqueta("Empresas"))
        c1.addWidget(self.l_emp)
        c2.addWidget(etiqueta("Gestiones"))
        c2.addWidget(self.l_ges)
        cuerpo.addLayout(c1, 3)
        cuerpo.addLayout(c2, 2)
        lay.addLayout(cuerpo, 1)
        self.b_nueva = boton("Nueva empresa…", "", 140)
        self.b_demo = boton("Empresa de demostración", "", 190)
        self.b_ok = boton("Abrir", "primario", 120)
        self.b_salir = boton("Salir", "", 100)
        lay.addLayout(hbox(self.b_nueva, self.b_demo, None, self.b_salir, self.b_ok))
        self.l_emp.currentRowChanged.connect(self.cargar_gestiones)
        self.l_emp.itemDoubleClicked.connect(lambda *_: self.abrir())
        self.l_ges.itemDoubleClicked.connect(lambda *_: self.abrir())
        self.b_ok.clicked.connect(self.abrir)
        self.b_salir.clicked.connect(self.reject)
        self.b_nueva.clicked.connect(self.nueva)
        self.b_nueva.setVisible(usuario["es_admin"])
        self.b_demo.setVisible(usuario["es_admin"])
        self.b_demo.clicked.connect(self.demo)
        self.cargar()

    def cargar(self, elegir: int | None = None) -> None:
        self.empresas = self.sis.empresas_de(self.usuario)
        self.l_emp.clear()
        for e in self.empresas:
            it = QListWidgetItem(f"{e['razon_social']}\nNIT {e['nit'] or 's/n'}  ·  {e['codigo']}")
            self.l_emp.addItem(it)
        if self.empresas:
            idx = next((i for i, e in enumerate(self.empresas) if e["id"] == elegir), 0)
            self.l_emp.setCurrentRow(idx)
        else:
            self.l_ges.clear()
        self.b_ok.setEnabled(bool(self.empresas))

    def cargar_gestiones(self, row: int) -> None:
        self.l_ges.clear()
        if row < 0:
            return
        self.gestiones = self.sis.gestiones(self.empresas[row]["id"])
        for g in self.gestiones:
            self.l_ges.addItem(f"Gestión {g['anio']}  ·  {'Abierta' if g['estado'] == 'A' else 'Cerrada'}")
        if self.gestiones:
            self.l_ges.setCurrentRow(next((i for i, g in enumerate(self.gestiones) if g["estado"] == "A"), 0))

    def nueva(self) -> None:
        r = dialogo_nueva_empresa(self.sis, self.usuario, self)
        if r:
            self.cargar(r[0])

    def demo(self) -> None:
        from datetime import date
        from ..demo import crear_empresa_demo
        if self.sis.db.scalar("SELECT COUNT(*) FROM empresa WHERE codigo='DEMO'", (), 0):
            aviso(self, "Ya existe la empresa de demostración (código DEMO).")
            return
        if not confirmar(self, "Se creará la empresa ficticia «Distribuidora Andina S.R.L.» con la gestión 2025 completa para practicar y ver los estados financieros. ¿Continuar?"):
            return
        ok, r = intentar(self, crear_empresa_demo, self.sis, self.usuario, 2025)
        if ok:
            self.cargar(r[0])

    def abrir(self) -> None:
        e, g = self.l_emp.currentRow(), self.l_ges.currentRow()
        if e < 0 or g < 0:
            aviso(self, "Seleccione una empresa y una gestión.")
            return
        self.seleccion = (self.empresas[e]["id"], self.gestiones[g]["id"])
        self.accept()
