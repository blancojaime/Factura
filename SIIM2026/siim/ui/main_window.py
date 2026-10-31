"""Ventana principal, estado de la aplicación, respaldo automático y bloqueo por inactividad."""
import sys
from datetime import datetime, timedelta

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

from .. import APP_FULL, APP_NAME, __version__
from ..core import backup as B
from ..core.paths import backup_dir
from ..services.base import Ctx
from . import theme
from .acceso import Login
from .actividades import ActividadesPage
from .inicio import InicioPage
from .liquidacion import LiquidacionPage
from .mantenimiento import MantenimientoPage
from .otros import OtrosPage
from .padron import PadronPage
from .recaudacion import RecaudacionPage
from .reportes import Calculadora, ReportesPage, Utilitarios
from .widgets import error, guarded, info, titulo


class AppState:
    def __init__(self, db, session, lic):
        self.db, self.session, self.lic, self.win = db, session, lic, None

    def ctx(self):
        return Ctx(self.db, self.session)

    def hacer_backup(self, label="auto", password=None):
        pw = password or (self.db.param("backup_clave") or None)
        extra = self.db.param("backup_externo") or None
        p = B.create_backup(self.db, backup_dir(), label, pw, meta=dict(usuario=self.session.usuario, municipio=self.db.param("municipio")), extra_dir=extra)
        B.apply_retention(backup_dir(), int(self.db.param("backup_retencion", "30") or 30))
        self.db.set_param("ultimo_backup", datetime.now().isoformat(timespec="seconds"))
        return p

    def refrescar_estado(self):
        if self.win:
            self.win.pintar_estado()

    def cerrar_tras_restaurar(self):
        QApplication.quit()


PAGINAS = [("Inicio", InicioPage, None), ("Empadronamiento (PMC)", PadronPage, "padron.ver"), ("Actividades económicas", ActividadesPage, "padron.ver"), ("Liquidación", LiquidacionPage, "liq.ejecutar"),
           ("Recaudación", RecaudacionPage, "rec.cobrar"), ("Otros ingresos", OtrosPage, "otros.fuc"), ("Reportes", ReportesPage, "reportes"), ("Deuda tributaria", Calculadora, "liq.ejecutar"),
           ("Mantenimiento", MantenimientoPage, "mant.ver"), ("Utilitarios", Utilitarios, "util.backup")]


class MainWindow(QMainWindow):
    def __init__(self, app: AppState):
        super().__init__()
        self.app = app
        app.win = self
        self.setWindowTitle(f"{APP_NAME} – {APP_FULL}")
        self.resize(1360, 820)
        root = QWidget(); self.setCentralWidget(root)
        h = QHBoxLayout(root); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(230)
        sl = QVBoxLayout(side); sl.setContentsMargins(0, 0, 0, 0); sl.setSpacing(0)
        b = QLabel(APP_NAME); b.setObjectName("brand"); sl.addWidget(b)
        bs = QLabel("Sistema Integrado de Ingresos Municipales"); bs.setObjectName("brandsub"); bs.setWordWrap(True); sl.addWidget(bs)
        self.nav = QListWidget(); self.nav.setObjectName("nav"); sl.addWidget(self.nav, 1)
        self.usr = QLabel(); self.usr.setStyleSheet("color:#A9BBD0;padding:10px 16px;font-size:8.5pt;"); self.usr.setWordWrap(True); sl.addWidget(self.usr)
        h.addWidget(side)
        self.stack = QStackedWidget(); h.addWidget(self.stack, 1)
        self.pages, self.idx = {}, {}
        for nombre, cls, perm in PAGINAS:
            if perm and not app.session.can(perm):
                continue
            it = QListWidgetItem(nombre)
            it.setData(Qt.UserRole, nombre)
            self.nav.addItem(it)
            self.idx[nombre] = (cls, None)
        self.nav.currentRowChanged.connect(self.ir)
        self.nav.setCurrentRow(0)
        self.estado = QLabel(); self.statusBar().addPermanentWidget(self.estado)
        self.pintar_estado()
        # respaldo automático y bloqueo por inactividad
        self.ultimo_input = datetime.now()
        QApplication.instance().installEventFilter(self)
        self.timer = QTimer(self); self.timer.timeout.connect(self.tic); self.timer.start(60_000)
        QTimer.singleShot(3000, self.tic)

    def ir(self, i):
        if i < 0:
            return
        nombre = self.nav.item(i).data(Qt.UserRole)
        cls, w = self.idx[nombre]
        if w is None:
            w = cls(self.app)
            self.idx[nombre] = (cls, w)
            self.stack.addWidget(w)
        self.stack.setCurrentWidget(w)
        if hasattr(w, "refrescar"):
            w.refrescar()

    def pintar_estado(self):
        s = self.app.session
        self.usr.setText(f"{s.nombre}\n{s.rol.title()}\n{self.app.db.param('municipio', '')[:60]}")
        st = self.app.lic.status()
        self.estado.setText(f"{st.mensaje}  ·  v{__version__}")
        self.statusBar().showMessage(f"Base de datos: {self.app.db.path}", 0)

    def eventFilter(self, o, e):
        if e.type() in (QEvent.MouseButtonPress, QEvent.KeyPress):
            self.ultimo_input = datetime.now()
        return super().eventFilter(o, e)

    def tic(self):
        db = self.app.db
        try:
            h = float(db.param("backup_auto_horas", "12") or 0)
            ult = db.param("ultimo_backup")
            if h > 0 and (not ult or datetime.now() - datetime.fromisoformat(ult) > timedelta(hours=h)):
                self.app.hacer_backup("auto")
            mins = int(db.param("sesion_minutos", "30") or 30)
            if datetime.now() - self.ultimo_input > timedelta(minutes=mins):
                self.bloquear()
            st = self.app.lic.status()
            if not st.ok:
                error(self, st.mensaje + "\nEl sistema se cerrará.", "Licencia")
                QApplication.quit()
        except Exception as e:                        # un fallo de respaldo no debe tumbar el sistema
            self.statusBar().showMessage(f"Aviso: {e}", 15000)

    def bloquear(self):
        self.hide()
        d = Login(self.app.db, "Sesión bloqueada por inactividad", self.app.session.usuario)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.show(); self.ultimo_input = datetime.now()
        else:
            QApplication.quit()

    def closeEvent(self, e):
        if QMessageBox.question(self, "Salir", "¿Desea cerrar el sistema?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            e.ignore(); return
        try:
            if self.app.db.param("backup_al_cerrar", "1") == "1":
                self.app.hacer_backup("al-cerrar")
        except Exception as ex:
            if QMessageBox.question(self, "Respaldo", f"No se pudo crear el respaldo de cierre:\n{ex}\n\n¿Cerrar de todos modos?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                e.ignore(); return
        self.app.ctx().log("LOGOUT")
        e.accept()
