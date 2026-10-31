"""Diálogos de acceso: configuración inicial, ingreso, cambio de clave y activación de licencia."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget)

from .. import APP_FULL, APP_NAME, __version__
from ..core import license as Lic
from ..core import security
from ..core.seed import PARAMS
from . import theme
from .widgets import btn, error, info


def _marca(sub):
    w = QWidget()
    w.setStyleSheet(f"background:{theme.NAVY};")
    l = QVBoxLayout(w)
    l.setContentsMargins(26, 30, 26, 30)
    a = QLabel(APP_NAME); a.setStyleSheet("color:white;font-size:26pt;font-weight:700;")
    b = QLabel(APP_FULL); b.setStyleSheet("color:#C9D6E6;font-size:10pt;"); b.setWordWrap(True)
    c = QLabel(sub); c.setStyleSheet("color:#9FB3CA;font-size:9pt;"); c.setWordWrap(True)
    l.addWidget(a); l.addWidget(b); l.addStretch(1); l.addWidget(c)
    w.setMinimumWidth(240)
    return w


class _Base(QDialog):
    def __init__(self, titulo, sub, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(_marca(sub))
        self.body = QVBoxLayout()
        self.body.setContentsMargins(30, 26, 30, 22)
        wrap = QWidget(); wrap.setObjectName("page"); wrap.setLayout(self.body)
        root.addWidget(wrap, 1)
        t = QLabel(titulo); t.setObjectName("titulo")
        self.body.addWidget(t)
        self.form = QFormLayout(); self.form.setVerticalSpacing(10)
        self.body.addLayout(self.form)
        self.msg = QLabel(""); self.msg.setObjectName("bad"); self.msg.setWordWrap(True)
        self.body.addWidget(self.msg)
        self.body.addStretch(1)


class FirstRun(_Base):
    def __init__(self):
        super().__init__("Configuración inicial", f"Versión {__version__}\nPrimer uso: defina el municipio y la cuenta del administrador. No existen contraseñas por defecto.")
        self.resize(820, 520)
        self.mun = QLineEdit(); self.mun.setPlaceholderText("GOBIERNO AUTÓNOMO MUNICIPAL DE …")
        self.nombre = QLineEdit(); self.user = QLineEdit("admin")
        self.p1 = QLineEdit(); self.p1.setEchoMode(QLineEdit.Password)
        self.p2 = QLineEdit(); self.p2.setEchoMode(QLineEdit.Password)
        for t, w in (("Municipio", self.mun), ("Nombre del administrador", self.nombre), ("Usuario", self.user), ("Contraseña", self.p1), ("Repetir contraseña", self.p2)):
            self.form.addRow(t, w)
        h = QHBoxLayout(); h.addStretch(1)
        h.addWidget(btn("Crear y continuar", self.ok, primary=True))
        self.body.addLayout(h)

    def ok(self):
        try:
            if not self.mun.text().strip() or not self.nombre.text().strip():
                raise ValueError("Complete municipio y nombre.")
            if self.p1.text() != self.p2.text():
                raise ValueError("Las contraseñas no coinciden.")
            self.datos = (self.mun.text().strip(), self.nombre.text().strip(), self.user.text().strip(), self.p1.text())
            prob = security.password_policy(self.p1.text())
            if prob:
                raise ValueError("Contraseña débil: " + ", ".join(prob))
        except ValueError as e:
            self.msg.setText(str(e)); return
        self.accept()


class Login(_Base):
    def __init__(self, db, municipio="", usuario_fijo=None):
        super().__init__("Ingreso al sistema", municipio or "Sistema Integrado de Ingresos Municipales")
        self.db, self.session = db, None
        self.resize(780, 440)
        self.user = QLineEdit(usuario_fijo or ""); self.user.setReadOnly(bool(usuario_fijo))
        self.pw = QLineEdit(); self.pw.setEchoMode(QLineEdit.Password)
        self.form.addRow("Usuario", self.user); self.form.addRow("Contraseña", self.pw)
        self.pw.returnPressed.connect(self.ok)
        h = QHBoxLayout(); h.addStretch(1)
        h.addWidget(btn("Salir", self.reject)); h.addWidget(btn("Ingresar", self.ok, primary=True))
        self.body.addLayout(h)
        (self.pw if usuario_fijo else self.user).setFocus()

    def ok(self):
        try:
            self.session = security.login(self.db, self.user.text(), self.pw.text())
        except security.AuthError as e:
            self.msg.setText(str(e)); self.pw.clear(); return
        u = self.db.one("SELECT cambiar_clave FROM usuarios WHERE id=?", (self.session.id,))
        if u["cambiar_clave"]:
            d = CambioClave(self.db, self.session.usuario)
            if d.exec() != QDialog.Accepted:
                self.msg.setText("Debe cambiar su contraseña para continuar."); return
        self.accept()


class CambioClave(_Base):
    def __init__(self, db, usuario):
        super().__init__("Cambio de contraseña", "Elija una contraseña nueva de al menos 8 caracteres con letras y números.")
        self.db, self.usuario = db, usuario
        self.resize(760, 380)
        self.p1 = QLineEdit(); self.p1.setEchoMode(QLineEdit.Password)
        self.p2 = QLineEdit(); self.p2.setEchoMode(QLineEdit.Password)
        self.form.addRow("Nueva contraseña", self.p1); self.form.addRow("Repetir", self.p2)
        h = QHBoxLayout(); h.addStretch(1); h.addWidget(btn("Guardar", self.ok, primary=True)); self.body.addLayout(h)

    def ok(self):
        if self.p1.text() != self.p2.text():
            self.msg.setText("Las contraseñas no coinciden."); return
        try:
            security.change_password(self.db, self.usuario, self.p1.text())
        except ValueError as e:
            self.msg.setText(str(e)); return
        self.accept()


class Activacion(_Base):
    """Activación offline: el cliente envía el código de instalación y recibe un archivo de licencia."""

    def __init__(self, lic_mgr, estado, puede_continuar=False):
        super().__init__("Activación de licencia", estado.mensaje)
        self.mgr, self.continuar = lic_mgr, False
        self.resize(900, 560)
        l = QLabel("1) Envíe este <b>código de instalación</b> a su proveedor (correo, WhatsApp).<br>2) Recibirá un archivo de licencia (.siimlic) o un texto.<br>3) Cárguelo aquí. No requiere Internet.")
        l.setWordWrap(True); l.setTextFormat(Qt.RichText)
        self.body.insertWidget(1, l)
        self.cod = QLineEdit(Lic.machine_code()); self.cod.setReadOnly(True)
        self.cod.setStyleSheet("font-size:18pt;font-weight:700;letter-spacing:2px;")
        self.form.addRow("Código de instalación", self.cod)
        self.txt = QPlainTextEdit(); self.txt.setPlaceholderText("Pegue aquí la licencia (SIIM1.xxxx.xxxx) o use «Cargar archivo»"); self.txt.setMaximumHeight(90)
        self.form.addRow("Licencia", self.txt)
        h = QHBoxLayout()
        h.addWidget(btn("Copiar código", lambda: QApplication.clipboard().setText(self.cod.text())))
        h.addWidget(btn("Cargar archivo…", self.archivo))
        h.addStretch(1)
        if puede_continuar:
            h.addWidget(btn("Continuar en modo de prueba", self.prueba))
        h.addWidget(btn("Salir", self.reject)); h.addWidget(btn("Activar", self.ok, primary=True))
        self.body.addLayout(h)

    def archivo(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Archivo de licencia", "", "Licencia (*.siimlic *.txt)")
        if fn:
            self.txt.setPlainText(open(fn, encoding="utf-8").read().strip())

    def prueba(self):
        self.continuar = True
        self.accept()

    def ok(self):
        st = self.mgr.install(self.txt.toPlainText())
        if st.estado == "LICENCIADO":
            info(self, st.mensaje, "Licencia activada")
            self.accept()
        else:
            self.msg.setText(st.mensaje)
