"""Centro de reportes (catálogo completo), calculadora de deuda tributaria y utilitarios (backups, mantenimiento de BD, licencia)."""
from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPlainTextEdit, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..calc.deuda import DeudaParams, calcular_deuda
from ..core import backup as B
from ..core import license as Lic
from ..core import security
from ..core.paths import backup_dir, data_dir, reports_dir
from ..reports import catalogo, engine
from ..reports import formularios as FM
from ..reports.engine import Col, fmt_num
from ..services.base import ServiceError, cotizacion, deuda_params, hoy, tasa_interes
from .padron import elegir_pmc
from .widgets import CrudDialog, DataTable, ExportBar, Field, FormPanel, btn, confirm, error, guarded, info, open_file, titulo

F = Field


class ReportesPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.rep, self.spec = app, None, None
        self.setObjectName("page")
        l = QVBoxLayout(self)
        l.addWidget(titulo("Centro de reportes", f"{len(catalogo.CATALOGO)} reportes disponibles. Todos se pueden ver, imprimir en PDF y exportar a Excel."))
        sp = QSplitter()
        l.addWidget(sp, 1)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        grupos = {}
        for k, r in catalogo.CATALOGO.items():
            g = grupos.get(r["grupo"])
            if g is None:
                g = QTreeWidgetItem([r["grupo"]])
                g.setFlags(Qt.ItemIsEnabled)
                self.tree.addTopLevelItem(g)
                grupos[r["grupo"]] = g
            it = QTreeWidgetItem([r["titulo"]])
            it.setData(0, Qt.UserRole, k)
            g.addChild(it)
        self.tree.expandAll()
        self.tree.currentItemChanged.connect(self.elegir)
        sp.addWidget(self.tree)
        right = QWidget()
        rl = QVBoxLayout(right)
        self.titulo = QLabel("Seleccione un reporte")
        self.titulo.setObjectName("titulo")
        rl.addWidget(self.titulo)
        self.form_box = QVBoxLayout()
        rl.addLayout(self.form_box)
        h = QHBoxLayout()
        self.b_run = btn("Generar vista previa", self.generar, primary=True)
        h.addWidget(self.b_run); h.addStretch(1)
        rl.addLayout(h)
        self.t = DataTable([])
        rl.addWidget(self.t, 1)
        self.exp = ExportBar(lambda: self.rep or self.generar(), app.ctx)
        rl.addWidget(self.exp)
        sp.addWidget(right)
        sp.setSizes([320, 900])
        self.form = None

    def elegir(self, cur, _):
        k = cur.data(0, Qt.UserRole) if cur else None
        if not k:
            return
        self.spec = catalogo.CATALOGO[k]
        self.titulo.setText(self.spec["titulo"])
        if self.form:
            self.form.setParent(None)
        gs = [(g, str(g)) for g in range(int(self.app.db.param("gestion_hasta")), int(self.app.db.param("gestion_desde")) - 1, -1)]
        campos = []
        for p in self.spec["params"]:
            kind = p["kind"]
            default = date.today().replace(month=1, day=1).isoformat() if p.get("default") == "ini_anio" else (p.get("default") if p.get("default") != "hoy" else date.today().isoformat())
            if kind == "choice":
                campos.append(F(p["name"], p["label"], "choice", p["choices"]))
            elif kind == "date":
                campos.append(F(p["name"], p["label"], "date", default=default))
            elif kind == "gestion":
                campos.append(F(p["name"], p["label"], "choice", [x[0] for x in gs]))
            elif kind == "int":
                campos.append(F(p["name"], p["label"], "int", default=p.get("default", 0), hi=9999))
            elif kind == "act":
                campos.append(F(p["name"], p["label"], "choice", [("", "(todas)")] + [(r[0], f"{r[0]} – {r[1][:50]}") for r in self.app.db.all("SELECT codigo, descripcion FROM act_tipos ORDER BY 1")]))
            else:
                campos.append(F(p["name"], p["label"], "text"))
        self.form = FormPanel(campos, columns=2 if len(campos) > 3 else 1) if campos else QLabel("Este reporte no requiere parámetros.")
        self.form_box.addWidget(self.form)
        self.rep = None
        self.t.set_cols([]); self.t.set_data([])

    @guarded
    def generar(self, *_):
        if not self.spec:
            raise ServiceError("Seleccione un reporte.")
        p = {}
        if isinstance(self.form, FormPanel):
            p = {k: v for k, v in self.form.values().items() if v not in (None, "")}
            for q in self.spec["params"]:
                if q["kind"] == "pmc" and q["name"] not in p:
                    x = elegir_pmc(self.app, self)
                    if not x:
                        return None
                    p[q["name"]] = x
        self.rep = catalogo.ejecutar(self.app.ctx(), self.spec["id"], **p)
        self.t.set_cols(self.rep.cols)
        self.t.set_data(self.rep.rows)
        self.titulo.setText(f"{self.rep.title}  ({len(self.rep.rows)} registros)")
        return self.rep


class Calculadora(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.d, self.datos = app, None, {}
        self.setObjectName("page")
        l = QVBoxLayout(self)
        l.addWidget(titulo("Calculadora de la Deuda Tributaria", "DT = TO × (1 + r/360)ⁿ + M (Art. 47 Ley 2492). Para deudas posteriores a la vigencia de la UFV (26/12/2002) y anteriores (con actualización por tipo de cambio). Cargue UFV y dólar en Mantenimiento o ingréselos manualmente."))
        self.form = FormPanel([F("to", "Tributo omitido en Bs (TO)", "float", hi=1e12, required=True), F("fv", "Fecha de vencimiento", "date"), F("fp", "Fecha de pago", "date"), F("persona", "Tipo de persona", "choice", [("N", "Natural"), ("J", "Jurídica")]),
                               F("auto", "Tomar UFV, dólar y tasa r de las tablas del sistema", "bool", default=True), F("ufv_fv", "UFV al vencimiento", "float", decimals=5), F("ufv_fp", "UFV a la fecha de pago", "float", decimals=5), F("r", "Tasa anual r (ej. 0,1082)", "float", decimals=5, default=0.1082),
                               F("usd_fv", "Dólar al vencimiento (deudas < 2002)", "float", decimals=4), F("usd_26", "Dólar al 26/12/2002", "float", decimals=4, default=7.49), F("ufv_26", "UFV al 26/12/2002", "float", decimals=5, default=1.00815),
                               F("multa", "Incluir multa por deberes formales", "bool", default=True), F("modo", "Cálculo de TO en UFV para la multa", "choice", [("DIVISION", "TO ÷ UFV (definición legal)"), ("SIIM_PDF", "TO × UFV (como en los Apuntes SIIM)")])], columns=2)
        l.addWidget(self.form)
        h = QHBoxLayout()
        h.addWidget(btn("Calcular", self.calc, primary=True)); h.addWidget(btn("Imprimir hoja de cálculo (PDF)", self.pdf)); h.addStretch(1)
        l.addLayout(h)
        self.t = DataTable([Col("c", "Componente", "text", 3), Col("v", "Valor", "text", 1)])
        l.addWidget(self.t, 1)

    @guarded
    def calc(self, *_):
        self.form.validate()
        v = self.form.values()
        db = self.app.db
        if v["auto"]:
            _, ufv_fv, _ = cotizacion(db, v["fv"])
            _, ufv_fp, _ = cotizacion(db, v["fp"])
            r = tasa_interes(db, v["fp"])
            usd_fv = cotizacion(db, v["fv"])[0] if v["fv"] < "2002-12-26" else None
            usd_26, ufv_26, _ = cotizacion(db, "2002-12-26") if v["fv"] < "2002-12-26" else (None, None, None)
        else:
            ufv_fv, ufv_fp, r = Decimal(str(v["ufv_fv"])), Decimal(str(v["ufv_fp"])), Decimal(str(v["r"]))
            usd_fv, usd_26, ufv_26 = Decimal(str(v["usd_fv"])), Decimal(str(v["usd_26"])), Decimal(str(v["ufv_26"]))
        p = deuda_params(db, v["persona"], bool(v["multa"]))
        p.r, p.modo_df_ufv = Decimal(r), v["modo"]
        try:
            self.d = calcular_deuda(v["to"], v["fv"], v["fp"], ufv_fv, ufv_fp, p, usd_fv=usd_fv, usd_26=usd_26, ufv_26=ufv_26)
        except ValueError as e:
            raise ServiceError(str(e))
        d = self.d
        self.datos = {"Fecha de vencimiento": v["fv"], "Fecha de pago": v["fp"], "UFV vencimiento": f"{ufv_fv}", "UFV pago": f"{ufv_fp}", "Tasa r": f"{float(r) * 100:.2f} %", "Persona": "Natural" if v["persona"] == "N" else "Jurídica"}
        f = fmt_num
        rows = [("Tributo omitido (TO)", f(d.to_bs)), ("Días de mora (n)", str(d.mora)), ("Mantenimiento de valor (Mv)", f(d.mv)), ("TO + Mv", f(d.to_mv)), ("Intereses", f(d.interes)),
                (f"Multa deberes formales ({f(d.multa_ufv)} UFV)", f(d.multa_bs)), ("Sanción administrativa", f(d.sancion)), ("DEUDA TRIBUTARIA TOTAL", f(d.total))]
        self.t.set_data([dict(c=a, v=b) for a, b in rows])

    @guarded
    def pdf(self, *_):
        if not self.d:
            raise ServiceError("Calcule primero.")
        p = reports_dir() / "deuda_tributaria.pdf"
        FM.generar(self.app.ctx(), FM.spec_calculo_deuda(self.d, self.datos), p)
        open_file(p)


class Utilitarios(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("page")
        l = QVBoxLayout(self)
        l.addWidget(titulo("Utilitarios del sistema", "Copias de seguridad verificadas, mantenimiento de la base de datos y estado de la licencia."))
        t = QTabWidget()
        t.addTab(self._backups(), "Copias de seguridad")
        t.addTab(self._bd(), "Base de datos")
        t.addTab(self._bitacora(), "Bitácora")
        t.addTab(self._licencia(), "Licencia / activación")
        l.addWidget(t)

    # ---- backups
    def _backups(self):
        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(QLabel(f"Carpeta de respaldos: {backup_dir()}"))
        bar = QHBoxLayout()
        for tx, s, p, d in (("Crear respaldo ahora", self.b_crear, True, False), ("Restaurar seleccionado…", self.b_restaurar, False, True), ("Verificar", self.b_verificar, False, False),
                            ("Copiar a USB / red…", self.b_copiar, False, False), ("Importar respaldo…", self.b_importar, False, False), ("Eliminar", self.b_borrar, False, True)):
            bar.addWidget(btn(tx, s, primary=p, danger=d))
        bar.addStretch(1)
        l.addLayout(bar)
        self.tb = DataTable([Col("nombre", "Archivo", "text", 3), Col("fecha", "Fecha", "text", 1.3), Col("mb", "Tamaño MB", "money"), Col("cifrado", "Cifrado")])
        l.addWidget(self.tb, 1)
        l.addWidget(QLabel("Recomendación: respaldo automático al cerrar el sistema + copia semanal a una unidad externa (USB o carpeta de red). Un respaldo que nunca se restauró en prueba no es un respaldo."))
        self.cargar_b()
        return w

    def cargar_b(self):
        self.tb.set_data([dict(nombre=b["nombre"], fecha=b["fecha"].strftime("%d/%m/%Y %H:%M"), mb=b["bytes"] / 1048576, cifrado="Sí" if b["cifrado"] else "No", path=b["path"]) for b in B.list_backups(backup_dir())])

    def _clave(self, cifrado=False, confirmar=False):
        pw = self.app.db.param("backup_clave", "")
        if cifrado:
            return QInputDialog.getText(self, "Contraseña del respaldo", "Contraseña:", QLineEdit.Password)[0] or None
        return pw or None

    @guarded
    def b_crear(self, *_):
        v = CrudDialog.ask("Nuevo respaldo", [F("etiqueta", "Etiqueta", default="manual"), F("clave", "Contraseña (opcional, cifra el respaldo)")], parent=self)
        if v:
            p = self.app.hacer_backup(v["etiqueta"] or "manual", v["clave"] or None)
            self.cargar_b()
            info(self, f"Respaldo creado y verificado:\n{p.name}")

    def _sel(self):
        r = self.tb.current_row()
        if not r:
            raise ServiceError("Seleccione un respaldo.")
        return r

    @guarded
    def b_verificar(self, *_):
        r = self._sel()
        pw = self._clave(True) if B.is_encrypted(r["path"]) else None
        m = B.verify_backup(r["path"], pw)
        info(self, f"Respaldo íntegro (SHA-256 verificado).\nCreado: {m['creado']} · Versión de esquema: {m['schema']} · {m['bytes'] / 1048576:.1f} MB")

    @guarded
    def b_restaurar(self, *_):
        if self.app.session.rol != "ADMINISTRADOR":
            raise ServiceError("Sólo el administrador puede restaurar.")
        r = self._sel()
        if not confirm(self, "La restauración REEMPLAZA todos los datos actuales por los del respaldo.\nSe creará antes un respaldo de seguridad automático.\n\n¿Desea continuar?"):
            return
        pw = self._clave(True) if B.is_encrypted(r["path"]) else None
        man, seg = B.restore_backup(self.app.db, r["path"], pw, backup_dir())
        info(self, f"Restauración completada (respaldo del {man['creado']}).\nSe guardó una copia previa: {seg.name}\n\nEl sistema se cerrará para recargar los datos.")
        self.app.cerrar_tras_restaurar()

    @guarded
    def b_copiar(self, *_):
        r = self._sel()
        d = QFileDialog.getExistingDirectory(self, "Carpeta destino (USB o red)")
        if d:
            import shutil
            shutil.copy2(r["path"], d)
            info(self, "Copiado.")

    @guarded
    def b_importar(self, *_):
        fn, _ = QFileDialog.getOpenFileName(self, "Respaldo", "", "Respaldo SIIM (*.siimbak)")
        if fn:
            import shutil
            shutil.copy2(fn, backup_dir())
            self.cargar_b()

    @guarded
    def b_borrar(self, *_):
        r = self._sel()
        if confirm(self, f"¿Eliminar {r['nombre']}?"):
            r["path"].unlink()
            self.cargar_b()

    # ---- base de datos
    def _bd(self):
        w = QWidget(); l = QVBoxLayout(w)
        self.bd_info = QPlainTextEdit(); self.bd_info.setReadOnly(True)
        bar = QHBoxLayout()
        for tx, s in (("Verificar integridad", self.verificar), ("Reorganizar índices", self.reindex), ("Compactar base de datos", self.compactar)):
            bar.addWidget(btn(tx, s, primary=(tx.startswith("Verificar"))))
        bar.addStretch(1)
        l.addLayout(bar)
        l.addWidget(self.bd_info, 1)
        self.verificar()
        return w

    @guarded
    def verificar(self, *_):
        ok, det = self.app.db.integrity_check()
        okc, bad = security.verify_audit_chain(self.app.db)
        import os
        sz = os.path.getsize(self.app.db.path) / 1048576
        self.bd_info.setPlainText(f"Archivo: {self.app.db.path}\nTamaño: {sz:.2f} MB · Esquema v{self.app.db.schema_version}\n\nIntegridad de la base de datos: {'CORRECTA' if ok else 'ERRORES: ' + '; '.join(det)}\n"
                                  f"Cadena de bitácora (anti-manipulación): {'CORRECTA' if okc else f'ALTERADA en el registro {bad}'}\n\nContribuyentes: {self.app.db.scalar('SELECT COUNT(*) FROM contribuyentes')} · Liquidaciones: {self.app.db.scalar('SELECT COUNT(*) FROM liquidaciones')} · Pagos: {self.app.db.scalar('SELECT COUNT(*) FROM pagos')}")

    @guarded
    def reindex(self, *_):
        self.app.hacer_backup("antes-reindexar")
        self.app.db.reindex(); self.verificar(); info(self, "Índices reorganizados.")

    @guarded
    def compactar(self, *_):
        self.app.hacer_backup("antes-compactar")
        self.app.db.compact(); self.verificar(); info(self, "Base de datos compactada.")

    def _bitacora(self):
        w = QWidget(); l = QVBoxLayout(w)
        bar = QHBoxLayout(); bar.addWidget(btn("Actualizar", self.cargar_bit, primary=True)); bar.addStretch(1); l.addLayout(bar)
        self.tbit = DataTable([Col("id", "N°", "int"), Col("fecha", "Fecha"), Col("usuario", "Usuario"), Col("accion", "Acción", "text", 1.5), Col("tabla", "Tabla"), Col("registro", "Reg."), Col("detalle", "Detalle", "text", 4)])
        l.addWidget(self.tbit, 1)
        self.cargar_bit()
        return w

    def cargar_bit(self, *_):
        self.tbit.set_data(self.app.db.all("SELECT id, fecha, usuario, accion, tabla, registro, substr(detalle,1,200) AS detalle FROM bitacora ORDER BY id DESC LIMIT 500"))

    def _licencia(self):
        w = QWidget(); l = QVBoxLayout(w)
        self.lic_lbl = QLabel(); self.lic_lbl.setObjectName("titulo"); self.lic_lbl.setWordWrap(True)
        l.addWidget(self.lic_lbl)
        l.addWidget(QLabel("Código de instalación de este equipo (envíelo a su proveedor para obtener la licencia):"))
        self.cod = QLineEdit(Lic.machine_code()); self.cod.setReadOnly(True); self.cod.setStyleSheet("font-size: 16pt; font-weight: 700; letter-spacing: 2px;")
        l.addWidget(self.cod)
        h = QHBoxLayout()
        h.addWidget(btn("Copiar código", lambda: __import__("PySide6.QtWidgets", fromlist=["QApplication"]).QApplication.clipboard().setText(self.cod.text())))
        h.addWidget(btn("Activar con archivo de licencia…", self.act_archivo, primary=True)); h.addWidget(btn("Pegar licencia…", self.act_texto)); h.addStretch(1)
        l.addLayout(h); l.addStretch(1)
        self.act_estado()
        return w

    def act_estado(self):
        st = self.app.lic.status()
        self.lic_lbl.setText(st.mensaje)

    @guarded
    def act_archivo(self, *_):
        fn, _ = QFileDialog.getOpenFileName(self, "Licencia", "", "Licencia SIIM (*.siimlic *.txt)")
        if fn:
            self._inst(open(fn, encoding="utf-8").read())

    @guarded
    def act_texto(self, *_):
        t, ok = QInputDialog.getMultiLineText(self, "Activar", "Pegue el texto de la licencia:")
        if ok:
            self._inst(t)

    def _inst(self, txt):
        st = self.app.lic.install(txt)
        self.app.ctx().log("LICENCIA", None, None, {"estado": st.estado})
        (info if st.estado == "LICENCIADO" else error)(self, st.mensaje)
        self.act_estado(); self.app.refrescar_estado()
