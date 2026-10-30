"""Administración: parámetros y normativa, usuarios, auditoría, copias de seguridad, cierre de gestión, consolidación y utilitarios."""
from __future__ import annotations

import os
import platform
import sys
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from .. import APP_NAME, __version__, backup
from ..permisos import OPCIONES, ROLES
from ..services.consolidacion import ConsolidacionService
from ..sistema import ErrorNegocio
from ..util import fdate, fmt, r2
from . import tema
from .base import ListaCRUD, Pantalla
from .formularios import Campo, FormDialog
from .widgets import CampoFecha, CampoImporte, Columna, Combo, TablaDatos, aviso, boton, confirmar, error, etiqueta, hbox, info, intentar


# ================================================================== parámetros
class ParametrosPantalla(Pantalla):
    titulo = "Parámetros y normativa"
    subtitulo = "Datos de la empresa, cuentas asociadas a cada operación automática y normativa laboral e impositiva vigente."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        self.tabs = QTabWidget()
        self.cuerpo.addWidget(self.tabs, 1)
        # --- empresa
        w = QWidget()
        l = QVBoxLayout(w)
        e = ctx.empresa
        self.f_emp: dict[str, QLineEdit] = {}
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        for i, (k, et) in enumerate([("razon_social", "Razón social"), ("nombre_comercial", "Nombre comercial"), ("nit", "NIT"), ("direccion", "Dirección"), ("ciudad", "Ciudad"), ("telefono", "Teléfono"),
                                     ("email", "Correo"), ("actividad", "Actividad económica"), ("rep_legal", "Representante legal"), ("matricula", "Matrícula de comercio")]):
            q = QLineEdit(e.get(k) or "")
            self.f_emp[k] = q
            g.addWidget(etiqueta(et), (i // 2) * 2, i % 2)
            g.addWidget(q, (i // 2) * 2 + 1, i % 2)
        l.addLayout(g)
        b = boton("Guardar datos de la empresa", "primario")
        b.clicked.connect(self.guardar_empresa)
        b.setEnabled(ctx.puede("ADM.PARAMETROS"))
        l.addWidget(b, 0, Qt.AlignLeft)
        l.addStretch(1)
        self.tabs.addTab(w, "Empresa")
        # --- cuentas
        self.t_cta = QTableWidget(0, 3)
        self.t_cta.setHorizontalHeaderLabels(["Parámetro", "Cuenta contable", "Descripción"])
        self.t_cta.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.t_cta.setColumnWidth(0, 200)
        self.t_cta.setColumnWidth(1, 330)
        self.t_cta.verticalHeader().setVisible(False)
        self.t_cta.setAlternatingRowColors(True)
        self.tabs.addTab(self._tab_cuentas(), "Cuentas de operaciones automáticas")
        # --- reglas
        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        self.r_it = QCheckBox("Calcular IT también en ventas sin factura")
        self.r_it.setChecked(ctx.param("IT_SIN_FACTURA") == "1")
        self.r_neg = QCheckBox("Permitir stock negativo")
        self.r_neg.setChecked(ctx.param("STOCK_NEGATIVO") == "1")
        self.r_pres = QCheckBox("Controlar presupuesto (impedir comprobantes que excedan lo presupuestado)")
        self.r_pres.setChecked(ctx.param("CONTROL_PRESUPUESTO") == "1")
        self.r_iue = QCheckBox("Mostrar provisión estimada del IUE en el Estado de Resultados")
        self.r_iue.setChecked(ctx.param("IUE_PROVISION") == "1")
        self.r_tc = CampoImporte(ctx.pnum("TC_DEFECTO", 6.96), 4)
        self.r_tc.setMaximumWidth(140)
        for c in (self.r_it, self.r_neg, self.r_pres, self.r_iue):
            l2.addWidget(c)
        l2.addWidget(etiqueta("Tipo de cambio por defecto (si no hay uno cargado para la fecha)"))
        l2.addWidget(self.r_tc)
        l2.addWidget(etiqueta("Nota sobre contingencias (Notas a los Estados Financieros)"))
        self.n_cont = QPlainTextEdit(ctx.param("NOTA_CONTINGENCIAS"))
        self.n_cont.setFixedHeight(70)
        l2.addWidget(self.n_cont)
        l2.addWidget(etiqueta("Nota sobre hechos posteriores"))
        self.n_post = QPlainTextEdit(ctx.param("NOTA_HECHOS_POSTERIORES"))
        self.n_post.setFixedHeight(70)
        l2.addWidget(self.n_post)
        b2 = boton("Guardar reglas", "primario")
        b2.clicked.connect(self.guardar_reglas)
        b2.setEnabled(ctx.puede("ADM.PARAMETROS"))
        l2.addWidget(b2, 0, Qt.AlignLeft)
        l2.addStretch(1)
        self.tabs.addTab(w2, "Reglas")
        # --- normativa
        self.t_norm = TablaDatos([Columna("clave", "Parámetro", 190), Columna("vigente_desde", "Vigente desde", 110, "date"), Columna("valor", "Valor", 130), Columna("descripcion", "Descripción", 360, estirar=True), Columna("fuente", "Fuente", 150)])
        w3 = QWidget()
        l3 = QVBoxLayout(w3)
        aviso_ = QLabel("Los valores reflejan la normativa vigente a octubre de 2026. Verifíquelos periódicamente en la Gaceta Oficial, el SIN y el MTEPS. Para un cambio, agregue un nuevo valor con su fecha de vigencia: los períodos anteriores conservan el valor que regía.")
        aviso_.setWordWrap(True)
        aviso_.setObjectName("sub")
        l3.addWidget(aviso_)
        l3.addWidget(self.t_norm, 1)
        bn = boton("Agregar / modificar vigencia", "primario")
        bn.clicked.connect(self.editar_norm)
        bn.setEnabled(ctx.puede("ADM.PARAMETROS"))
        l3.addWidget(bn, 0, Qt.AlignLeft)
        self.tabs.addTab(w3, "Normativa vigente")
        self.t_norm.doble_clic.connect(self.editar_norm)
        self.refrescar()

    def _tab_cuentas(self):
        from ..seed import PARAMETROS
        self.combos: dict[str, Combo] = {}
        opciones = [(c["codigo"], f"{c['codigo']}  {c['nombre']}") for c in self.ctx.cuentas.listar(solo_movimiento=True)]
        claves = sorted(k for k in PARAMETROS if k.startswith("CTA_"))
        self.t_cta.setRowCount(len(claves))
        desc = {"CTA_CAJA": "Caja general para contado", "CTA_CF_IVA": "Crédito fiscal IVA (compras)", "CTA_DF_IVA": "Débito fiscal IVA (ventas)", "CTA_IT_GASTO": "Gasto por IT",
                "CTA_IT_PAGAR": "IT por pagar", "CTA_CXC": "Clientes (ventas a crédito)", "CTA_CXP": "Proveedores (compras a crédito)", "CTA_INVENT": "Inventario de mercaderías",
                "CTA_VENTAS": "Ingresos por ventas", "CTA_COSTO_VTA": "Costo de ventas", "CTA_SUELDOS": "Sueldos y salarios", "CTA_RESULTADO": "Resultado de la gestión (cierre)",
                "CTA_RESULT_ACUM": "Resultados acumulados (apertura)"}
        for i, k in enumerate(claves):
            self.t_cta.setItem(i, 0, QTableWidgetItem(k))
            self.t_cta.item(i, 0).setFlags(Qt.ItemIsEnabled)
            cb = Combo()
            cb.cargar(opciones, None)
            cb.set_valor(self.ctx.param(k))
            self.combos[k] = cb
            self.t_cta.setCellWidget(i, 1, cb)
            self.t_cta.setItem(i, 2, QTableWidgetItem(desc.get(k, "")))
            self.t_cta.item(i, 2).setFlags(Qt.ItemIsEnabled)
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(self.t_cta, 1)
        b = boton("Guardar cuentas", "primario")
        b.clicked.connect(self.guardar_cuentas)
        b.setEnabled(self.ctx.puede("ADM.PARAMETROS"))
        l.addWidget(b, 0, Qt.AlignLeft)
        return w

    def refrescar(self) -> None:
        self.t_norm.cargar(self.ctx.normativa.listar())

    def guardar_empresa(self) -> None:
        ok, _ = intentar(self, self.ctx.sistema.actualizar_empresa, self.ctx.empresa["id"], **{k: v.text().strip() for k, v in self.f_emp.items()})
        if ok:
            self.ctx.empresa.update({k: v.text().strip() for k, v in self.f_emp.items()})
            info(self, "Datos de la empresa guardados.")
            if self.ventana:
                self.ventana.actualizar_estado()

    def guardar_cuentas(self) -> None:
        for k, cb in self.combos.items():
            if cb.valor():
                self.ctx.set_param(k, cb.valor())
        info(self, "Cuentas guardadas.")

    def guardar_reglas(self) -> None:
        c = self.ctx
        c.set_param("IT_SIN_FACTURA", "1" if self.r_it.isChecked() else "0")
        c.set_param("STOCK_NEGATIVO", "1" if self.r_neg.isChecked() else "0")
        c.set_param("CONTROL_PRESUPUESTO", "1" if self.r_pres.isChecked() else "0")
        c.set_param("IUE_PROVISION", "1" if self.r_iue.isChecked() else "0")
        c.set_param("TC_DEFECTO", str(self.r_tc.valor()))
        c.set_param("NOTA_CONTINGENCIAS", self.n_cont.toPlainText().strip())
        c.set_param("NOTA_HECHOS_POSTERIORES", self.n_post.toPlainText().strip())
        info(self, "Reglas guardadas.")

    def editar_norm(self, f=None) -> None:
        f = f if isinstance(f, dict) else None
        campos = [Campo("clave", "Parámetro", "txt", True), Campo("vigente_desde", "Vigente desde (aaaa-mm-dd)", "txt", True), Campo("valor", "Valor", "txt", True, ancho=2),
                  Campo("descripcion", "Descripción", ancho=2), Campo("fuente", "Fuente / norma", ancho=2)]
        v = dict(f) if f else {"vigente_desde": date.today().isoformat()}
        FormDialog("Normativa", campos, v, lambda x: self.ctx.normativa.guardar(x["clave"], x["vigente_desde"], x["valor"], x["descripcion"], x["fuente"]), parent=self.ventana or self).exec()
        self.refrescar()


# ================================================================== usuarios
class PermisosDialog(QDialog):
    def __init__(self, sis, uid: int, empresa: dict, nombre: str, parent=None):
        super().__init__(parent)
        self.sis, self.uid, self.empresa = sis, uid, empresa
        self.setWindowTitle(f"Permisos de {nombre}")
        self.resize(560, 620)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        h = QLabel(f"Permisos de {nombre} en {empresa['razon_social']}")
        h.setObjectName("h1")
        h.setWordWrap(True)
        lay.addWidget(h)
        top = QHBoxLayout()
        self.rol = Combo([(k, v) for k, v in ROLES.items() if k != "ADMIN"] + [("ADMIN", ROLES["ADMIN"])])
        self.rol.cargar([("", "(personalizado)")] + list(ROLES.items()))
        self.rol.set_valor(sis.rol(uid, empresa["id"]) or "")
        top.addWidget(etiqueta("Rol predefinido"))
        top.addWidget(self.rol, 1)
        lay.addLayout(top)
        self.lista = QListWidget()
        actuales = sis.permisos(uid, empresa["id"])
        grupo = None
        self.items: dict[str, QListWidgetItem] = {}
        for clave, nom, g in OPCIONES:
            if g != grupo:
                grupo = g
                it = QListWidgetItem(g.upper())
                it.setFlags(Qt.NoItemFlags)
                f = it.font()
                f.setBold(True)
                it.setFont(f)
                self.lista.addItem(it)
            it = QListWidgetItem(nom)
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Checked if clave in actuales else Qt.Unchecked)
            it.setData(Qt.UserRole, clave)
            self.lista.addItem(it)
            self.items[clave] = it
        lay.addWidget(self.lista, 1)
        ok, ca = boton("Guardar", "primario", 110), boton("Cancelar", "", 100)
        lay.addLayout(hbox(None, ca, ok))
        ok.clicked.connect(self.guardar)
        ca.clicked.connect(self.reject)
        self.rol.currentIndexChanged.connect(self.aplicar_rol)

    def aplicar_rol(self) -> None:
        from ..permisos import permisos_de_rol
        r = self.rol.valor()
        if r:
            ps = set(permisos_de_rol(r))
            for k, it in self.items.items():
                it.setCheckState(Qt.Checked if k in ps else Qt.Unchecked)

    def guardar(self) -> None:
        try:
            sel = [k for k, it in self.items.items() if it.checkState() == Qt.Checked]
            if self.rol.valor():
                self.sis.asignar_empresa(self.uid, self.empresa["id"], self.rol.valor())
            else:
                self.sis.asignar_empresa(self.uid, self.empresa["id"], "OPERADOR")
            self.sis.guardar_permisos(self.uid, self.empresa["id"], sel)
        except Exception as ex:  # noqa: BLE001
            error(self, ex)
            return
        self.accept()


class UsuariosPantalla(ListaCRUD):
    titulo = "Usuarios y permisos"
    subtitulo = "Cada usuario accede solo a las empresas y opciones que se le asignen."

    def __init__(self, ctx, ventana=None):
        cols = [Columna("login", "Usuario", 110), Columna("nombre", "Nombre", 240, estirar=True), Columna("rol", "Rol en esta empresa", 160), Columna("es_admin", "Admin.", 60, "bool"),
                Columna("activo", "Activo", 60, "bool"), Columna("ultimo", "Último acceso", 150)]
        super().__init__(ctx, cols, self.datos, [("Nuevo usuario", self.nuevo, "primario"), ("Permisos…", self.permisos, ""), ("Modificar", self.editar, ""), ("Restablecer clave", self.reset, ""),
                                                 ("Eliminar", self.eliminar, "peligro")], True, ventana, doble_clic=self.permisos)

    def datos(self):
        f = self.ctx.sistema.listar_usuarios()
        for u in f:
            u["rol"] = "Administrador" if u["es_admin"] else ROLES.get(self.ctx.sistema.rol(u["id"], self.ctx.empresa["id"]), "(sin acceso)").split(" (")[0]
            u["ultimo"] = (u["ultimo_acceso"] or "").replace("T", " ")
        return f

    def nuevo(self, _=None):
        campos = [Campo("login", "Usuario", "txt", True), Campo("nombre", "Nombre completo", "txt", True), Campo("clave", "Contraseña inicial", "txt", True), Campo("email", "Correo"),
                  Campo("rol", "Rol en esta empresa", "combo", True, opciones=[(k, v) for k, v in ROLES.items() if k != "ADMIN"]), Campo("es_admin", "Administrador del sistema", "check")]

        def guardar(v):
            uid = self.ctx.sistema.crear_usuario(v["login"], v["nombre"], v["clave"], v["es_admin"], v["email"])
            self.ctx.sistema.asignar_empresa(uid, self.ctx.empresa["id"], v["rol"])
        FormDialog("Nuevo usuario", campos, {"rol": "OPERADOR"}, guardar, "El usuario deberá cambiar la contraseña en su primer ingreso.", self.ventana or self).exec()

    def editar(self, f):
        if f:
            campos = [Campo("nombre", "Nombre", "txt", True), Campo("email", "Correo"), Campo("activo", "Activo", "check"), Campo("es_admin", "Administrador", "check")]
            FormDialog(f"Usuario {f['login']}", campos, f, lambda v: self.ctx.sistema.actualizar_usuario(f["id"], v["nombre"], v["email"], v["activo"], v["es_admin"]), parent=self.ventana or self).exec()

    def permisos(self, f):
        if f:
            PermisosDialog(self.ctx.sistema, f["id"], self.ctx.empresa, f["nombre"], self.ventana or self).exec()

    def reset(self, f):
        if f:
            FormDialog("Restablecer contraseña", [Campo("clave", "Nueva contraseña temporal", "txt", True)], None,
                       lambda v: self.ctx.sistema.cambiar_clave(f["id"], v["clave"], True), "El usuario deberá cambiarla al ingresar.", self.ventana or self).exec()

    def eliminar(self, f):
        if f and confirmar(self, f"¿Eliminar al usuario {f['login']}?", peligro=True):
            self.ctx.sistema.eliminar_usuario(f["id"])


class AuditoriaPantalla(ListaCRUD):
    titulo = "Auditoría del sistema"
    subtitulo = "Registro de ingresos y operaciones relevantes por usuario, fecha y hora."

    def __init__(self, ctx, ventana=None):
        self.desde = CampoFecha(date(ctx.gestion["anio"], 1, 1))
        self.desde.set_fecha(date.today().replace(day=1))
        self.hasta = CampoFecha(date.today())
        cols = [Columna("fecha_h", "Fecha y hora", 150), Columna("login", "Usuario", 90), Columna("modulo", "Módulo", 130), Columna("accion", "Acción", 150), Columna("detalle", "Detalle", 400, estirar=True), Columna("equipo", "Equipo", 120)]
        super().__init__(ctx, cols, self.datos, [("Informe PDF/Excel", lambda f: ventana.informe("auditoria"), "")], True, ventana, filtros=[etiqueta("Desde"), self.desde, etiqueta("Hasta"), self.hasta])
        for w in (self.desde, self.hasta):
            w.dateChanged.connect(lambda *_: self.refrescar())

    def datos(self):
        f = self.ctx.sistema.auditoria(self.desde.fecha(), self.hasta.fecha())
        for a in f:
            a["fecha_h"] = a["fecha"].replace("T", " ")
        return f


# ==================================================================== backup
class BackupPantalla(Pantalla):
    titulo = "Copias de seguridad"
    subtitulo = "Respaldo verificable (.cbk con huella SHA-256) de la empresa o de todo el sistema, y restauración."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        self.sis = ctx.sistema
        fila = QHBoxLayout()
        b1 = boton("Respaldar esta empresa", "primario")
        b2 = boton("Respaldar TODO el sistema")
        b3 = boton("Restaurar desde archivo…", "peligro")
        b4 = boton("Verificar un respaldo…")
        for b in (b1, b2, b4, b3):
            fila.addWidget(b)
        fila.addStretch(1)
        self.cuerpo.addLayout(fila)
        self.l_info = QLabel(f"Carpeta de respaldos: {os.path.join(self.sis.raiz, 'backups')}")
        self.l_info.setObjectName("sub")
        self.cuerpo.addWidget(self.l_info)
        self.tabla = TablaDatos([Columna("fecha", "Fecha", 150), Columna("tipo", "Tipo", 120), Columna("archivo", "Archivo", 400, estirar=True), Columna("tamano_mb", "MB", 70, "num"), Columna("resultado", "Resultado", 100)])
        self.cuerpo.addWidget(self.tabla, 1)
        b1.clicked.connect(lambda: self.hacer(ctx.empresa["id"]))
        b2.clicked.connect(lambda: self.hacer(None))
        b3.clicked.connect(self.restaurar)
        b4.clicked.connect(self.verificar)
        b1.setEnabled(ctx.puede("ADM.BACKUP"))
        b2.setEnabled(ctx.puede("ADM.BACKUP") and ctx.usuario["es_admin"])
        b3.setEnabled(ctx.puede("ADM.RESTAURAR") and ctx.usuario["es_admin"])
        self.refrescar()

    def refrescar(self) -> None:
        f = self.sis.db.query("SELECT * FROM backup_log ORDER BY id DESC LIMIT 200")
        for x in f:
            x["fecha"] = x["fecha"].replace("T", " ")
        self.tabla.cargar(f)

    def hacer(self, eid) -> None:
        ok, ruta = intentar(self, backup.crear_backup, self.sis, eid)
        if ok:
            info(self, f"Copia de seguridad creada:\n{ruta}")
            self.refrescar()

    def verificar(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "Verificar copia", os.path.join(self.sis.raiz, "backups"), "Copias ContaBol (*.cbk)")
        if ruta:
            ok, meta = intentar(self, backup.verificar, ruta)
            if ok:
                info(self, f"Copia VÁLIDA.\nGenerada: {meta['fecha']}\nEmpresas: {len(meta['empresas'])}  ·  Gestiones: {len(meta['gestiones'])}")

    def restaurar(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "Restaurar copia", os.path.join(self.sis.raiz, "backups"), "Copias ContaBol (*.cbk)")
        if not ruta:
            return
        if not confirmar(self, "La restauración reemplaza los datos actuales de las empresas incluidas en la copia (se crea antes una copia de seguridad de lo actual).\n\n¿Continuar?", "Restaurar", True):
            return
        self.ctx.db.checkpoint()
        self.ctx.cerrar()
        ok, r = intentar(self, backup.restaurar, self.sis, ruta, self.ctx.usuario)
        if ok:
            info(self, f"Restauración completada: {r['empresas']} empresa(s), {r['gestiones']} gestión(es).\nLa aplicación se reiniciará la sesión para cargar los datos.")
        if self.ventana:
            self.ventana.accion_salida = "cambiar"
            self.ventana.close()


# =============================================================== cierre de gestión
class CierrePantalla(Pantalla):
    titulo = "Ajustes y cierre de gestión"
    subtitulo = "Ajuste por inflación (opcional), diferencia de cambio, asiento de cierre, cierre de la gestión y apertura de la siguiente."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        pasos = QVBoxLayout()
        pasos.setSpacing(10)
        self.f_inf = CampoFecha(ctx.fin, ctx.inicio, ctx.fin)
        self.f_dif = CampoFecha(ctx.fin, ctx.inicio, ctx.fin)
        self.tc = CampoImporte(ctx.tc.dolar(ctx.fin), 4)
        self.f_cie = CampoFecha(ctx.fin, ctx.inicio, ctx.fin)
        pasos.addWidget(self._paso("1. Ajuste por inflación y tenencia de bienes (UFV)",
                                   "Actualiza las cuentas ajustables con la variación de la UFV. La Norma Contable N° 3 está suspendida contablemente desde 2020 (CTNAC 03/2020); úselo solo si su política lo requiere o para efectos tributarios.",
                                   [("Fecha", self.f_inf)], [("Vista previa", lambda: self.inflacion(False), ""), ("Registrar", lambda: self.inflacion(True), "primario")]))
        pasos.addWidget(self._paso("2. Diferencia de cambio", "Actualiza en bolivianos los saldos en dólares de las cuentas con moneda extranjera al tipo de cambio de cierre.",
                                   [("Fecha", self.f_dif), ("T.C. final", self.tc)], [("Vista previa", lambda: self.cambio(False), ""), ("Registrar", lambda: self.cambio(True), "primario")]))
        pasos.addWidget(self._paso("3. Asiento de cierre", "Salda ingresos y gastos contra «Resultado de la gestión». Los estados financieros se emiten antes del cierre y no se alteran.",
                                   [("Fecha", self.f_cie)], [("Generar asiento de cierre", self.cierre, "primario")]))
        pasos.addWidget(self._paso("4. Cerrar gestión y abrir la siguiente", "La gestión cerrada queda en solo lectura. La apertura traslada saldos, existencias, cuentas por cobrar/pagar, activos y empleados.",
                                   [], [("Cerrar gestión", self.cerrar, "exito"), ("Reabrir gestión", self.reabrir, ""), ("Abrir nueva gestión…", self.nueva, "primario")]))
        self.cuerpo.addLayout(pasos)
        self.cuerpo.addWidget(etiqueta("Vista previa", "h1"))
        self.tabla = TablaDatos([Columna("codigo", "Código", 130), Columna("nombre", "Cuenta", 260, estirar=True), Columna("saldo", "Saldo", 120, "money"), Columna("ajuste", "Ajuste", 120, "money")])
        self.cuerpo.addWidget(self.tabla, 1)
        self.lbl = QLabel("")
        self.cuerpo.addWidget(self.lbl)

    def _paso(self, titulo, texto, campos, botones):
        f = QFrame()
        f.setObjectName("panel")
        l = QVBoxLayout(f)
        l.setContentsMargins(16, 10, 16, 10)
        l.setSpacing(4)
        t = QLabel(titulo)
        t.setStyleSheet(f"font-weight:600; color:{tema.AZUL};")
        d = QLabel(texto)
        d.setObjectName("sub")
        d.setWordWrap(True)
        l.addWidget(t)
        l.addWidget(d)
        fila = QHBoxLayout()
        for et, w in campos:
            fila.addWidget(etiqueta(et))
            fila.addWidget(w)
        fila.addStretch(1)
        for tx, fn, tp in botones:
            b = boton(tx, tp)
            b.clicked.connect(fn)
            b.setEnabled(self.ctx.puede("CONT.CIERRE") and (self.ctx.abierta or tx in ("Reabrir gestión", "Abrir nueva gestión…")))
            fila.addWidget(b)
        l.addLayout(fila)
        return f

    def _mostrar(self, r, titulo):
        filas = [{"codigo": x["codigo"], "nombre": x["nombre"], "saldo": x.get("saldo", x.get("saldo_bs")), "ajuste": x["ajuste"]} for x in r["filas"]]
        self.tabla.cargar(filas)
        self.lbl.setText(f"{titulo}: {len(filas)} cuenta(s) · efecto neto Bs {fmt(r['neto'])}" + ("  — REGISTRADO" if r.get("comprobante_id") else ""))

    def inflacion(self, reg: bool) -> None:
        if reg and not confirmar(self, "Se registrará el comprobante de ajuste por inflación. ¿Continuar?"):
            return
        ok, r = intentar(self, self.ctx.gestiones.ajuste_inflacion, self.f_inf.fecha(), reg)
        if ok:
            self._mostrar(r, "Ajuste por inflación")

    def cambio(self, reg: bool) -> None:
        if reg and not confirmar(self, "Se registrará el comprobante de diferencia de cambio. ¿Continuar?"):
            return
        ok, r = intentar(self, self.ctx.gestiones.diferencia_cambio, self.f_dif.fecha(), self.tc.valor(), reg)
        if ok:
            self._mostrar(r, "Diferencia de cambio")

    def cierre(self) -> None:
        if confirmar(self, "Se generará el asiento de cierre de ingresos y gastos. ¿Continuar?"):
            ok, _ = intentar(self, self.ctx.gestiones.generar_cierre, self.f_cie.fecha())
            if ok:
                info(self, "Asiento de cierre generado.")

    def cerrar(self) -> None:
        if confirmar(self, f"Al cerrar la gestión {self.ctx.gestion['anio']} solo podrá consultarla. ¿Cerrarla?", "Cerrar gestión", True):
            ok, _ = intentar(self, self.ctx.gestiones.cerrar_gestion)
            if ok and self.ventana:
                info(self, "Gestión cerrada.")
                self.ventana.refrescar_todo()

    def reabrir(self) -> None:
        ok, _ = intentar(self, self.ctx.gestiones.reabrir_gestion)
        if ok and self.ventana:
            info(self, "Gestión reabierta.")
            self.ventana.refrescar_todo()

    def nueva(self) -> None:
        if not confirmar(self, f"Se creará la gestión {self.ctx.gestion['anio'] + 1} con los saldos finales de la actual. ¿Continuar?"):
            return
        ok, gid = intentar(self, self.ctx.gestiones.abrir_nueva_gestion)
        if ok:
            info(self, f"Gestión {self.ctx.gestion['anio'] + 1} creada. Use Archivo > Cambiar de empresa o gestión para abrirla.")


class ConsolidarPantalla(Pantalla):
    titulo = "Consolidación de empresas"
    subtitulo = "Suma por código de cuenta las empresas y gestiones seleccionadas (se recomienda que usen el mismo plan de cuentas)."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        self.srv = ConsolidacionService(ctx.sistema, ctx.usuario)
        self.disp = self.srv.disponibles()
        self.lista = QListWidget()
        for d in self.disp:
            it = QListWidgetItem(f"{d['razon_social']}  ·  gestión {d['anio']}")
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Unchecked)
            self.lista.addItem(it)
        top = QHBoxLayout()
        self.desde, self.hasta = CampoFecha(ctx.inicio), CampoFecha(ctx.fin)
        self.nivel = Combo([(i, f"Nivel {i}") for i in range(1, 7)])
        self.nivel.set_valor(4)
        b = boton("Consolidar", "primario")
        for et, w in (("Desde", self.desde), ("Hasta", self.hasta), ("Detalle", self.nivel)):
            top.addWidget(etiqueta(et))
            top.addWidget(w)
        top.addStretch(1)
        top.addWidget(b)
        self.cuerpo.addWidget(self.lista, 1)
        self.cuerpo.addLayout(top)
        self.tabla = TablaDatos([Columna("codigo", "Código", 130), Columna("nombre", "Cuenta", 300, estirar=True), Columna("debe", "Debe", 120, "money"), Columna("haber", "Haber", 120, "money"),
                                 Columna("saldo_d", "Saldo deudor", 120, "money"), Columna("saldo_h", "Saldo acreedor", 120, "money")])
        self.cuerpo.addWidget(self.tabla, 2)
        b.clicked.connect(self.consolidar)

    def consolidar(self) -> None:
        ids = [self.disp[i]["gestion_id"] for i in range(self.lista.count()) if self.lista.item(i).checkState() == Qt.Checked]
        ok, f = intentar(self, self.srv.balance, ids, self.desde.fecha(), self.hasta.fecha(), self.nivel.valor())
        if ok:
            self.tabla.cargar(f)


# ====================================================================== utilitarios
class UtilitariosPantalla(Pantalla):
    titulo = "Utilitarios y verificación"
    subtitulo = "Verificación de integridad contable, mantenimiento de la base de datos y diagnóstico."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        fila = QHBoxLayout()
        b1 = boton("Verificar contabilidad", "primario")
        b2 = boton("Compactar base de datos")
        b3 = boton("Recalcular existencias de inventario")
        for b in (b1, b2, b3):
            fila.addWidget(b)
        fila.addStretch(1)
        self.cuerpo.addLayout(fila)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setStyleSheet("font-family: 'Consolas','DejaVu Sans Mono',monospace; font-size:10pt; background:white;")
        self.cuerpo.addWidget(self.txt, 1)
        b1.clicked.connect(self.verificar)
        b2.clicked.connect(self.compactar)
        b3.clicked.connect(self.recalcular)
        self.verificar()

    def verificar(self) -> None:
        c, db = self.ctx, self.ctx.db
        L = [f"VERIFICACIÓN DE {c.empresa['razon_social']} - GESTIÓN {c.gestion['anio']}", "=" * 72]

        def chk(ok, msg_ok, msg_err, aviso_=False):
            L.append(("[OK] " if ok else ("[AVISO] " if aviso_ else "[ERROR] ")) + (msg_ok if ok else msg_err))
        n = db.scalar("SELECT COUNT(*) FROM comprobante WHERE estado='V' AND ABS(debe_bs-haber_bs)>0.01", (), 0)
        chk(n == 0, "Todos los comprobantes vigentes cuadran.", f"{n} comprobante(s) descuadrados.")
        n2 = db.scalar("SELECT COUNT(*) FROM comprobante c WHERE c.estado='V' AND ABS(c.debe_bs-(SELECT COALESCE(SUM(debe_bs),0) FROM comp_det WHERE comprobante_id=c.id))>0.01", (), 0)
        chk(n2 == 0, "Los totales de cabecera coinciden con el detalle.", f"{n2} comprobante(s) con totales inconsistentes.")
        b = c.estados.balance_general(c.fin, 3)
        chk(b["cuadra"], "El balance general cuadra (Activo = Pasivo + Patrimonio).", f"El balance no cuadra: diferencia {b['diferencia']:,.2f}")
        flujo = c.estados.flujo_directo(c.inicio, c.fin)
        chk(flujo["cuadra"], "El flujo de efectivo concilia con el disponible.", "El flujo de efectivo no concilia con el saldo de caja y bancos.")
        falt = [k for k, v in c.params().items() if k.startswith("CTA_") and not c.cuenta_por_codigo(v)]
        chk(not falt, "Todas las cuentas parametrizadas existen.", "Cuentas inexistentes en parámetros: " + ", ".join(falt))
        chk(c.tc.existe(c.inicio), "Hay tipo de cambio al inicio de la gestión.", "No hay tipo de cambio cargado al inicio de la gestión.", True)
        chk(c.tc.ufv(c.fin) > 0, "Hay UFV cargada.", "No hay UFV cargada (necesaria para activos fijos y ajustes).", True)
        neg = db.scalar("SELECT COUNT(*) FROM item WHERE stock<-0.0001", (), 0)
        chk(neg == 0, "No hay ítems con stock negativo.", f"{neg} ítem(s) con stock negativo.", True)
        inv_k, inv_c = c.inventario.valor_total(c.fin), c.cuentas.saldo(c.cuenta_param("CTA_INVENT"), c.fin)
        chk(abs(inv_k - inv_c) < 0.05, f"El inventario valorado ({inv_k:,.2f}) coincide con la contabilidad.", f"El inventario valorado ({inv_k:,.2f}) difiere de la cuenta contable ({inv_c:,.2f}).", True)
        chk(c.db.integrity_check() == "ok", "Integridad de la base de datos SQLite correcta.", "La verificación de integridad de SQLite falló: restaure una copia.")
        L.append("")
        L.append(f"Comprobantes: {db.scalar('SELECT COUNT(*) FROM comprobante', (), 0)}  ·  Cuentas: {db.scalar('SELECT COUNT(*) FROM cuenta', (), 0)}  ·  Ítems: {db.scalar('SELECT COUNT(*) FROM item', (), 0)}  ·  Terceros: {db.scalar('SELECT COUNT(*) FROM tercero', (), 0)}")
        ruta = c.db.path
        L.append(f"Archivo de datos: {ruta}  ({os.path.getsize(ruta) / 1048576:.1f} MB)")
        self.txt.setPlainText("\n".join(L))

    def compactar(self) -> None:
        if confirmar(self, "Se compactará el archivo de datos (VACUUM). ¿Continuar?"):
            ok, _ = intentar(self, self.ctx.db.vacuum)
            if ok:
                info(self, "Base de datos compactada.")
                self.verificar()

    def recalcular(self) -> None:
        info(self, "El inventario se recalcula automáticamente con cada movimiento. Use «Verificar contabilidad» para comparar el inventario valorado con el saldo contable.")


class AcercaDe(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de ContaBol")
        self.setFixedSize(640, 430)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 20)
        fila = QHBoxLayout()
        lg = QLabel()
        lg.setPixmap(tema.logo_pixmap(84))
        t = QVBoxLayout()
        t1 = QLabel("ContaBol")
        t1.setStyleSheet(f"font-size:26pt; font-weight:600; color:{tema.AZUL};")
        t2 = QLabel(f"Sistema Contable Integrado · Versión {__version__}")
        t2.setObjectName("sub")
        t.addWidget(t1)
        t.addWidget(t2)
        fila.addWidget(lg)
        fila.addSpacing(14)
        fila.addLayout(t, 1)
        lay.addLayout(fila)
        txt = QLabel("Sistema contable comercial y de costos conforme a la normativa contable, impositiva y laboral de Bolivia: IVA 13%, IT 3%, IUE 25%, RC-IVA, "
                     "aportes AFP/CNS/Pro-Vivienda, bono de antigüedad, aguinaldo e indemnización, libros de compras y ventas y los seis estados financieros "
                     "(Balance General, Estado de Resultados, Evolución del Patrimonio, Flujo de Efectivo directo e indirecto y Notas).\n\n"
                     "• Multiempresa y multigestión\n• Informes en pantalla, PDF y Excel\n• Copias de seguridad verificables\n• Datos en SQLite (WAL) sin límite práctico de tamaño\n\n"
                     f"Datos: {ctx.sistema.raiz}\nUsuario: {ctx.usuario['nombre']}\nPython {platform.python_version()} · {platform.system()} {platform.release()}")
        txt.setWordWrap(True)
        txt.setAlignment(Qt.AlignTop)
        lay.addWidget(txt, 1)
        b = boton("Cerrar", "primario", 100)
        b.clicked.connect(self.accept)
        lay.addLayout(hbox(None, b))
