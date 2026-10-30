"""Ventana principal: menú por módulos, accesos rápidos, pestañas, tablero de inicio y barra de estado."""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMenu, QMenuBar, QScrollArea, QStatusBar, QTabBar, QTabWidget,
                               QToolBar, QToolButton, QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from ..util import fmt, mes_nombre
from . import tema
from .base import Pantalla
from .widgets import Banner, GraficoBarras, Tarjeta, aviso, boton, confirmar, error, etiqueta, hbox, info


class Inicio(Pantalla):
    titulo = "Inicio"

    def __init__(self, ctx, ventana):
        self.subtitulo = f"{ctx.empresa['razon_social']}  ·  Gestión {ctx.gestion['anio']}"
        super().__init__(ctx, ventana)
        self.contenedor = QVBoxLayout()
        self.cuerpo.addLayout(self.contenedor, 1)
        self.refrescar()

    def refrescar(self) -> None:
        while self.contenedor.count():
            it = self.contenedor.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                self._vaciar(it.layout())
        c = self.ctx
        db = c.db
        mes = min(max(date.today().month if date.today().year == c.gestion["anio"] else 12, 1), 12)
        per = f"{c.gestion['anio']}{mes:02d}"
        ventas = db.scalar("SELECT COALESCE(SUM(total),0) FROM venta WHERE estado='V' AND substr(fecha,1,7)=?", (f"{c.gestion['anio']}-{mes:02d}",), 0.0)
        compras = db.scalar("SELECT COALESCE(SUM(total),0) FROM compra WHERE estado='V' AND substr(fecha,1,7)=?", (f"{c.gestion['anio']}-{mes:02d}",), 0.0)
        cobrar = db.scalar("SELECT COALESCE(SUM(saldo),0) FROM venta WHERE estado='V'", (), 0.0)
        pagar = db.scalar("SELECT COALESCE(SUM(saldo),0) FROM compra WHERE estado='V'", (), 0.0)
        efectivo = c.estados._efectivo(c.fin)
        res = c.estados.resultado(c.inicio, c.fin)
        fila = QHBoxLayout()
        fila.setSpacing(14)
        for t, v, col in ((f"Ventas de {mes_nombre(mes)}", ventas, tema.VERDE), (f"Compras de {mes_nombre(mes)}", compras, tema.AZUL), ("Cuentas por cobrar", cobrar, tema.AZUL),
                          ("Cuentas por pagar", pagar, tema.ROJO), ("Caja y bancos", efectivo, tema.AZUL), ("Resultado acumulado", res, tema.VERDE if res >= 0 else tema.ROJO)):
            fila.addWidget(Tarjeta(t, "Bs " + fmt(v), col))
        self.contenedor.addLayout(fila)
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(14)
        pan = QFrame()
        pan.setObjectName("panel")
        pl = QVBoxLayout(pan)
        pl.setContentsMargins(16, 12, 16, 12)
        pl.addWidget(etiqueta("Ventas y compras por mes (Bs)", "h1"))
        v12, c12 = [0.0] * 12, [0.0] * 12
        for r in db.query("SELECT CAST(substr(fecha,6,2) AS INTEGER) m, SUM(total) t FROM venta WHERE estado='V' GROUP BY m"):
            v12[r["m"] - 1] = r["t"]
        for r in db.query("SELECT CAST(substr(fecha,6,2) AS INTEGER) m, SUM(total) t FROM compra WHERE estado='V' GROUP BY m"):
            c12[r["m"] - 1] = r["t"]
        pl.addWidget(GraficoBarras([mes_nombre(m)[:3] for m in range(1, 13)], v12, c12))
        cuerpo.addWidget(pan, 3)
        der = QVBoxLayout()
        acc = QFrame()
        acc.setObjectName("panel")
        al = QVBoxLayout(acc)
        al.setContentsMargins(16, 12, 16, 12)
        al.addWidget(etiqueta("Accesos rápidos", "h1"))
        for texto, op, fn in (("Nuevo comprobante", "CONT.COMPROBANTES", self.ventana.nuevo_comprobante), ("Registrar venta", "COM.VENTAS", lambda: self.ventana.nuevo_documento(True)),
                              ("Registrar compra", "COM.COMPRAS", lambda: self.ventana.nuevo_documento(False)), ("Libro de ventas IVA", "IVA.REGISTRO", lambda: self.ventana.abrir_libro_iva("V")),
                              ("Estados financieros", "CONT.REPORTES", lambda: self.ventana.informe("estados_financieros"))):
            b = boton(texto)
            b.setEnabled(c.puede(op))
            b.clicked.connect(fn)
            al.addWidget(b)
        der.addWidget(acc)
        av = QFrame()
        av.setObjectName("panel")
        vl = QVBoxLayout(av)
        vl.setContentsMargins(16, 12, 16, 12)
        vl.addWidget(etiqueta("Avisos", "h1"))
        avisos = []
        if not c.tc.existe(c.inicio):
            avisos.append("• No hay tipo de cambio cargado al inicio de la gestión.")
        if c.tc.ufv(c.fin) <= 0:
            avisos.append("• No hay UFV cargada (activos fijos y ajustes).")
        bajos = db.scalar("SELECT COUNT(*) FROM item WHERE activo=1 AND es_servicio=0 AND stock_min>0 AND stock<stock_min", (), 0)
        if bajos:
            avisos.append(f"• {bajos} ítem(s) por debajo del stock mínimo.")
        venc = db.scalar("SELECT COUNT(*) FROM venta WHERE estado='V' AND saldo>0.004 AND vencimiento<?", (date.today().isoformat(),), 0)
        if venc:
            avisos.append(f"• {venc} documento(s) por cobrar vencidos.")
        if not c.abierta:
            avisos.append("• La gestión está CERRADA (solo consulta).")
        if not avisos:
            avisos.append("• Sin avisos pendientes. ✔")
        for a in avisos:
            l = QLabel(a)
            l.setWordWrap(True)
            vl.addWidget(l)
        vl.addStretch(1)
        der.addWidget(av, 1)
        cuerpo.addLayout(der, 2)
        self.contenedor.addLayout(cuerpo, 1)

    def _vaciar(self, lay) -> None:
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                self._vaciar(it.layout())


class VentanaPrincipal(QMainWindow):
    def __init__(self, sis, usuario: dict, ctx):
        super().__init__()
        self.sis, self.usuario, self.ctx = sis, usuario, ctx
        self.accion_salida = "salir"   # salir | cambiar | sesion
        self.setWindowTitle(f"{APP_NAME} - Sistema Contable Integrado")
        self.setWindowIcon(tema.icono("CB", "white", tema.AZUL, 64))
        self.resize(1360, 820)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.cerrar_pestana)
        self.setCentralWidget(self.tabs)
        self._claves: dict[str, QWidget] = {}
        self.estado = QStatusBar()
        self.setStatusBar(self.estado)
        self.l_emp, self.l_ges, self.l_usr, self.l_tc, self.l_hora = (QLabel() for _ in range(5))
        for l in (self.l_ges, self.l_usr, self.l_tc, self.l_hora):
            self.estado.addPermanentWidget(l)
        self.estado.addWidget(self.l_emp, 1)
        from .menu import construir_menu
        construir_menu(self)
        self.inicio()
        self.actualizar_estado()
        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.actualizar_estado)
        self.reloj.start(30000)

    # ----------------------------------------------------------------- pestañas
    def inicio(self) -> None:
        self.tabs.clear()
        self._claves.clear()
        self.abrir_pantalla(Inicio(self.ctx, self), "Inicio", "Inicio", cerrable=False)

    def abrir_pantalla(self, w: QWidget, titulo: str | None = None, clave: str | None = None, cerrable: bool = True) -> QWidget:
        if clave and clave in self._claves:
            ex = self._claves[clave]
            self.tabs.setCurrentWidget(ex)
            if hasattr(ex, "refrescar"):
                ex.refrescar()
            w.deleteLater()
            return ex
        i = self.tabs.addTab(w, titulo or getattr(w, "titulo", "Pantalla"))
        if not cerrable:
            self.tabs.tabBar().setTabButton(i, QTabBar.RightSide, None)
        if clave:
            self._claves[clave] = w
        self.tabs.setCurrentIndex(i)
        return w

    def abrir(self, clase, *args, clave: str | None = None, **kw) -> QWidget:
        clave = clave or clase.__name__
        if clave in self._claves:
            return self.abrir_pantalla(None, clave=clave)  # type: ignore[arg-type]
        try:
            w = clase(self.ctx, *args, ventana=self, **kw)
        except Exception as ex:  # noqa: BLE001
            error(self, ex)
            return None  # type: ignore[return-value]
        return self.abrir_pantalla(w, getattr(w, "titulo", clase.__name__), clave)

    def cerrar_pestana(self, i: int) -> None:
        w = self.tabs.widget(i)
        for k, v in list(self._claves.items()):
            if v is w:
                del self._claves[k]
        self.tabs.removeTab(i)
        w.deleteLater()

    def cerrar_actual(self) -> None:
        i = self.tabs.currentIndex()
        if i > 0:
            self.cerrar_pestana(i)

    def cerrar_todas(self) -> None:
        while self.tabs.count() > 1:
            self.cerrar_pestana(self.tabs.count() - 1)

    def refrescar_todo(self) -> None:
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if hasattr(w, "refrescar"):
                try:
                    w.refrescar()
                except Exception:  # noqa: BLE001
                    pass
        self.actualizar_estado()

    # ----------------------------------------------------------------- estado
    def actualizar_estado(self) -> None:
        c = self.ctx
        self.l_emp.setText(f"{c.empresa['razon_social']}   ·   NIT {c.empresa['nit'] or 's/n'}")
        self.l_ges.setText(f"Gestión {c.gestion['anio']} " + ("" if c.abierta else "(CERRADA)"))
        self.l_usr.setText(f"Usuario: {c.usuario['login']}")
        self.l_tc.setText(f"T.C. {c.tc.dolar(date.today() if c.inicio <= date.today() <= c.fin else c.fin):.2f}  ·  UFV {c.tc.ufv(date.today() if c.inicio <= date.today() <= c.fin else c.fin):.5f}")
        self.l_hora.setText(datetime.now().strftime("%d/%m/%Y  %H:%M"))

    # ------------------------------------------------------------- atajos usados
    def nuevo_comprobante(self) -> None:
        from .p_contab import ComprobanteDialog
        if ComprobanteDialog(self.ctx, None, self).exec():
            self.refrescar_todo()

    def nuevo_documento(self, venta: bool) -> None:
        from .p_comercial import DocumentoDialog
        if DocumentoDialog(self.ctx, venta, self).exec():
            self.refrescar_todo()

    def abrir_libro_iva(self, libro: str) -> None:
        from .p_iva import LibroIvaPantalla
        self.abrir(LibroIvaPantalla, libro, clave=f"LibroIva.{libro}")

    def informe(self, id_: str, valores=None, pedir=True) -> None:
        from .reportes_ui import abrir_informe
        abrir_informe(self, self.ctx, id_, valores, pedir)

    def closeEvent(self, ev):
        if self.accion_salida == "salir" and not confirmar(self, "¿Desea salir de ContaBol?\nSe generará una copia de seguridad automática al cerrar.", "Salir"):
            ev.ignore()
            return
        ev.accept()
