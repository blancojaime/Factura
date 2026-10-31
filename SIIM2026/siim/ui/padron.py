"""Empadronamiento (PMC): búsqueda multiacceso, F-019 / F-027 / F-035 y registro de inmuebles, vehículos, actividades y publicidad."""
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QTabWidget, QVBoxLayout, QWidget, QDialogButtonBox)

from ..core import seed as S
from ..reports import formularios as FM
from ..reports.engine import Col
from ..services import padron
from ..services import recaudacion as R
from ..services.base import ServiceError, hoy
from .widgets import CrudDialog, DataTable, Field, FormPanel, btn, confirm, error, guarded, info, open_file, titulo

F = Field
SINO = ["NINGUNO"]


def _zonas(db):
    return [("", "—")] + [(r[0], f"{r[0]} – {r[1]}") for r in db.all("SELECT codigo, descripcion FROM zonas ORDER BY 1")]


def _barrios(db):
    return [("", "—")] + [(r[0], f"{r[0]} – {r[1]}") for r in db.all("SELECT codigo, descripcion FROM barrios ORDER BY 1")]


def campos_contribuyente(db):
    return [F("persona", "Tipo de persona", "choice", [("N", "Natural"), ("J", "Jurídica"), ("S", "Sucesión indivisa")], default="N"),
            F("tipo_doc", "Tipo de documento", "choice", S.TIPOS_DOC), F("nro_doc", "N° de documento", maxlen=20), F("expedido", "Expedido", "choice", [""] + S.EXPEDIDO),
            F("paterno", "Apellido paterno", maxlen=40), F("materno", "Apellido materno", maxlen=40), F("nombre", "Nombre(s)", maxlen=60),
            F("nit", "NIT / RUC", maxlen=20), F("razon_social", "Razón social", maxlen=100),
            F("zona", "Zona", "choice", _zonas(db)), F("barrio", "Barrio / urbanización", "choice", _barrios(db)), F("tipo_via", "Tipo de vía", "choice", S.TIPOS_VIA),
            F("calle", "Calle / avenida", maxlen=80), F("numero", "N° casa", maxlen=10), F("bloque", "Bloque", maxlen=10), F("piso", "Piso", maxlen=5), F("dpto", "Dpto.", maxlen=10),
            F("telefono", "Teléfono", maxlen=20), F("celular", "Celular", maxlen=20), F("email", "Correo electrónico", maxlen=80), F("medidor", "N° medidor de luz", maxlen=20), F("casilla", "Casilla", maxlen=10),
            F("benemerito", "Benemérito de la Campaña del Chaco", "bool"), F("fecha_nacimiento", "Fecha de nacimiento (adulto mayor)", "date?"), F("observaciones", "Observaciones / ubicación", "area")]


def campos_objeto(db, tabla):
    if tabla == "inmuebles":
        return [F("tipo", "Tipo de inmueble", "choice", S.TIPOS_INMUEBLE, required=True), F("zona", "Zona", "choice", _zonas(db)), F("barrio", "Barrio", "choice", _barrios(db)), F("tipo_via", "Tipo de vía", "choice", S.TIPOS_VIA),
                F("calle", "Calle", required=True), F("numero", "N°"), F("cod_catastral", "Código catastral (Dist-Manz-Lote)"), F("cod_censal", "Código censal"), F("nro_ddrr", "Matrícula Derechos Reales"),
                F("material_via", "Material de la vía", "choice", S.MATERIALES), F("superficie", "Superficie del terreno m²", "float"), F("inclinacion", "Inclinación", "choice", S.INCLINACIONES),
                F("luz", "Luz", "bool"), F("agua", "Agua", "bool"), F("alcantarillado", "Alcantarillado", "bool"), F("telefono", "Teléfono", "bool"),
                F("calidad", "Calidad de construcción", "choice", [""] + sorted(set(S.CALIDADES_CASA + S.CALIDADES_DEPTO))), F("sup_construida", "Superficie construida m²", "float"), F("anio_construccion", "Año de construcción", "int", lo=0, hi=2100),
                F("otras_construcciones", "Otras construcciones (valor Bs)", "float", hi=1e12), F("valor_declarado", "Valor declarado (rural) Bs", "float", hi=1e12), F("exento", "Exención", "choice", S.EXENCIONES)]
    if tabla == "vehiculos":
        return [F("placa", "Placa", required=True, maxlen=12), F("pta", "PTA"), F("tipo", "Tipo de vehículo", "choice", S.TIPOS_VEHICULO, required=True), F("marca", "Marca"), F("modelo", "Modelo"),
                F("procedencia", "Procedencia", "choice", S.PROCEDENCIAS), F("pais", "País (si otra)"), F("anio_fab", "Año de fabricación", "int", lo=1900, hi=2100, default=date.today().year), F("anio_imp", "Año de importación", "int", lo=0, hi=2100),
                F("uso", "Uso", "choice", S.USOS_VEHICULO), F("cilindrada", "Cilindrada cc", "int", hi=99999), F("toneladas", "Capacidad (toneladas)", "float"), F("puertas", "N° de puertas", "int", lo=0, hi=10, default=4),
                F("doble_traccion", "Doble tracción", "bool"), F("turbo", "Motor turbo", "bool"), F("chasis", "Chasis (>1,5 t)", "choice", S.CHASIS), F("carroceria", "Carrocería (>1,5 t)", "choice", S.CARROCERIAS), F("plazas", "N° de plazas", "int", hi=200),
                F("revalorizacion", "Valor residual contable (jurídicas) Bs", "float", hi=1e12), F("nro_motor", "N° de motor"), F("nro_chasis", "N° de chasis"), F("color", "Color"), F("exento", "Exención", "choice", S.EXENCIONES)]
    if tabla == "actividades":
        tipos = [(r[0], f"{r[0]} – {r[1][:60]}") for r in db.all("SELECT codigo, descripcion FROM act_tipos ORDER BY 1")]
        ciiu = [("", "—")] + [(r[0], f"{r[0]} – {r[1][:60]}") for r in db.all("SELECT codigo, descripcion FROM ciiu WHERE es_detalle=1 ORDER BY 1")]
        return [F("act", "Tipo de actividad", "choice", tipos, required=True), F("cat", "Categoría", "choice", [], required=True), F("nombre_comercial", "Nombre del establecimiento", required=True), F("nit", "NIT"),
                F("matricula_comercio", "Matrícula de comercio (SEPREC)"), F("ciiu", "CIIU / CAEB", "choice", ciiu), F("fecha_inicio", "Fecha de inicio de actividades", "date", required=True), F("fecha_cese", "Fecha de cese", "date?"),
                F("habitualidad", "Habitualidad", "choice", ["PERMANENTE", "EVENTUAL"]), F("superficie", "Superficie m²", "float"), F("consumo_elect", "Consumo eléctrico promedio kWh/mes", "float", hi=1e9),
                F("zona", "Zona", "choice", _zonas(db)), F("barrio", "Barrio", "choice", _barrios(db)), F("tipo_via", "Tipo de vía", "choice", S.TIPOS_VIA), F("calle", "Calle"), F("numero", "N°"), F("telefono", "Teléfono"),
                F("exento", "Exención", "choice", S.EXENCIONES)]
    if tabla == "publicidad":
        return [F("tipo", "Tipo de anuncio", "choice", S.TIPOS_PUBLICIDAD, required=True), F("descripcion", "Descripción / leyenda", required=True), F("ubicacion", "Ubicación"), F("ancho", "Ancho m", "float"), F("alto", "Alto m", "float"),
                F("fecha_instalacion", "Fecha de instalación", "date?"), F("exento", "Exención", "choice", S.EXENCIONES)]


COLS = {
    "inmuebles": [Col("id", "ID", "int"), Col("tipo", "Tipo"), Col("calle", "Calle", "text", 2), Col("numero", "N°"), Col("zona", "Zona"), Col("superficie", "Terreno m²", "money"), Col("sup_construida", "Constr. m²", "money"), Col("exento", "Exención")],
    "vehiculos": [Col("id", "ID", "int"), Col("placa", "Placa"), Col("tipo", "Tipo"), Col("marca", "Marca"), Col("modelo", "Modelo"), Col("anio_fab", "Año"), Col("cilindrada", "cc", "int"), Col("procedencia", "Procedencia")],
    "actividades": [Col("id", "ID", "int"), Col("nombre_comercial", "Establecimiento", "text", 2), Col("act", "Act"), Col("cat", "Cat"), Col("zona", "Zona"), Col("superficie", "m²", "money"), Col("fecha_inicio", "Inicio", "date"), Col("estado_licencia", "Licencia")],
    "publicidad": [Col("id", "ID", "int"), Col("tipo", "Tipo"), Col("descripcion", "Descripción", "text", 2), Col("ubicacion", "Ubicación"), Col("ancho", "Ancho", "money"), Col("alto", "Alto", "money")],
}


def _rules_inmueble(f: FormPanel):
    t = f.get("tipo")
    en = lambda names, v: [f.w[n].setEnabled(v) for n in names]
    en(["material_via", "inclinacion", "luz", "agua", "alcantarillado", "telefono"], t != "RURAL" and t != "DEPARTAMENTO")
    en(["superficie"], t in ("CASA", "TERRENO"))
    en(["calidad", "sup_construida", "anio_construccion", "otras_construcciones"], t in ("CASA", "DEPARTAMENTO"))
    en(["valor_declarado"], t == "RURAL")


def _rules_vehiculo(f: FormPanel):
    tipo = (f.get("tipo") or "")
    moto = tipo in ("MOTOCICLETA", "MOTONETA", "TRIMOVIL", "CUADRATRACK")
    pesado = (f.get("toneladas") or 0) > 1.5
    for n in ("procedencia",):
        f.w[n].setEnabled(not moto)
    for n in ("doble_traccion", "turbo", "puertas"):
        f.w[n].setEnabled(not moto and not pesado)
    for n in ("chasis", "carroceria", "plazas"):
        f.w[n].setEnabled(not moto and pesado)


class ObjetoDialog(CrudDialog):
    def __init__(self, app, tabla, values=None, parent=None):
        super().__init__("Registro de " + tabla, campos_objeto(app.db, tabla), None, parent, columns=2, width=860)
        self.app, self.tabla = app, tabla
        f = self.form
        if tabla == "actividades":
            f.w["act"].currentIndexChanged.connect(self._cats)
            self._cats()
        if values:
            f.load(values)
            if tabla == "actividades":
                self._cats()
                f.set("cat", values["cat"])
        rules = {"inmuebles": _rules_inmueble, "vehiculos": _rules_vehiculo}.get(tabla)
        if rules:
            for n in [x for x in ("tipo", "toneladas") if x in f.w]:
                w = f.w[n]
                (w.currentIndexChanged if isinstance(w, QComboBox) else w.valueChanged).connect(lambda *_: rules(f))
            rules(f)

    def _cats(self, *_):
        a = self.form.get("act")
        self.form.set_choices("cat", [(r[0], f"{r[0]} – {r[1][:70]}") for r in self.app.db.all("SELECT cat, descripcion FROM act_categorias WHERE act=? ORDER BY cat", (a,))], keep=False)


class ObjetoTab(QWidget):
    def __init__(self, dlg, tabla):
        super().__init__()
        self.dlg, self.tabla = dlg, tabla
        l = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.b_ins = btn("Insertar", self.nuevo, primary=True)
        self.b_mod = btn("Modificar", self.editar)
        self.b_del = btn("Eliminar (baja F-035)", self.baja, danger=True)
        for b in (self.b_ins, self.b_mod, self.b_del):
            bar.addWidget(b)
        if tabla == "actividades":
            self.b_lic = btn("Emitir / renovar licencia", self.licencia)
            self.b_pdf = btn("Imprimir licencia", self.imprimir_lic)
            bar.addWidget(self.b_lic)
            bar.addWidget(self.b_pdf)
        bar.addStretch(1)
        l.addLayout(bar)
        self.t = DataTable(COLS[tabla])
        self.t.doble_click.connect(lambda *_: self.editar())
        l.addWidget(self.t)

    def aplicar_modo(self, modo, habilitado):
        self.b_ins.setEnabled(habilitado and modo != "F-035")
        self.b_mod.setEnabled(habilitado and modo != "F-035")
        self.b_del.setEnabled(habilitado and modo == "F-035")

    def cargar(self):
        if self.dlg.pmc:
            self.t.set_data(padron.objetos(self.dlg.app.db, self.tabla, self.dlg.pmc))

    @guarded
    def nuevo(self, *_):
        d = ObjetoDialog(self.dlg.app, self.tabla, parent=self)
        if d.exec() == QDialog.Accepted:
            padron.guardar_objeto(self.dlg.app.ctx(), self.tabla, self.dlg.pmc, d.form.values(), None, self.dlg.modo)
            self.cargar()

    @guarded
    def editar(self, *_):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un registro.")
        d = ObjetoDialog(self.dlg.app, self.tabla, r, self)
        if d.exec() == QDialog.Accepted:
            padron.guardar_objeto(self.dlg.app.ctx(), self.tabla, self.dlg.pmc, d.form.values(), r["id"], self.dlg.modo)
            self.cargar()

    @guarded
    def baja(self, *_):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un registro.")
        v = CrudDialog.ask("Baja (F-035)", [F("fecha", "Fecha de baja", "date"), F("motivo", "Motivo", required=True)], parent=self)
        if v and confirm(self, "La baja es lógica (queda en bitácora) y deja de liquidarse. ¿Continuar?"):
            padron.baja_objeto(self.dlg.app.ctx(), self.tabla, r["id"], v["fecha"], v["motivo"], self.dlg.nro_orden)
            self.cargar()

    @guarded
    def licencia(self, *_):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione una actividad.")
        try:
            nro, vence = padron.emitir_licencia(self.dlg.app.ctx(), r["id"])
        except ServiceError as e:
            if "vencida" in str(e) and confirm(self, str(e) + "\n\n¿Emitir de todos modos (requiere autorización del supervisor)?") and self.dlg.app.session.can("rec.anular"):
                nro, vence = padron.emitir_licencia(self.dlg.app.ctx(), r["id"], permitir_con_deuda=True)
            else:
                raise
        info(self, f"Licencia {nro} vigente hasta {vence}.")
        self.cargar()

    @guarded
    def imprimir_lic(self, *_):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione una actividad.")
        from ..core.paths import reports_dir
        p = reports_dir() / f"licencia_{r['id']}.pdf"
        FM.generar(self.dlg.app.ctx(), FM.spec_licencia(self.dlg.app.ctx(), r["id"]), p)
        open_file(p)


class RespaldoDialog(CrudDialog):
    pass


class ContribuyenteDialog(QDialog):
    def __init__(self, app, modo="F-019", pmc=None, nro_orden="", parent=None):
        super().__init__(parent)
        self.app, self.modo, self.pmc, self.nro_orden = app, modo, pmc, nro_orden
        self.setWindowTitle({"F-019": "Nueva incorporación (F-019)", "F-027": "Modificación / incorporación (F-027)", "F-035": "Desincorporación (F-035)"}[modo])
        self.resize(1000, 700)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.lbl = QLabel()
        self.lbl.setObjectName("titulo")
        self.estado = QLabel()
        top.addWidget(self.lbl)
        top.addStretch(1)
        top.addWidget(self.estado)
        lay.addLayout(top)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.form = FormPanel(campos_contribuyente(app.db), columns=2)
        from PySide6.QtWidgets import QScrollArea
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(self.form)
        self.tabs.addTab(sc, "Datos del contribuyente")
        self.tabs_obj = {}
        for t, n in (("inmuebles", "Inmuebles"), ("vehiculos", "Vehículos"), ("actividades", "Actividades económicas"), ("publicidad", "Publicidad")):
            w = ObjetoTab(self, t)
            self.tabs_obj[t] = w
            self.tabs.addTab(w, n)
        self.form.w["persona"].currentIndexChanged.connect(self._persona)
        bar = QHBoxLayout()
        self.b_save = btn("Guardar datos (F10)", self.guardar, primary=True)
        bar.addWidget(self.b_save)
        bar.addWidget(btn("Kardex PDF", self.kardex))
        bar.addStretch(1)
        bar.addWidget(btn("Cerrar", self.accept))
        lay.addLayout(bar)
        if pmc:
            self.form.load(app.db.one("SELECT * FROM contribuyentes WHERE pmc=?", (pmc,)))
        self._persona()
        self._refresh()
        if modo == "F-035":
            self.form.setEnabled(False)
            self.b_save.setEnabled(False)
            self.tabs.setCurrentIndex(1)

    def _persona(self, *_):
        j = self.form.get("persona") == "J"
        for n in ("paterno", "materno", "nombre", "fecha_nacimiento", "benemerito"):
            self.form.w[n].setEnabled(not j)
        self.form.w["razon_social"].setEnabled(j)

    def _refresh(self):
        c = self.app.db.one("SELECT estado FROM contribuyentes WHERE pmc=?", (self.pmc,)) if self.pmc else None
        est = c["estado"] if c else "NUEVO"
        self.lbl.setText(f"PMC {self.pmc}" if self.pmc else "PMC (se asigna al guardar)")
        self.estado.setText(f"Registro {est}")
        self.estado.setObjectName("ok" if est == "ACTIVO" else "warn")
        self.estado.setStyleSheet("")
        self.estado.style().unpolish(self.estado); self.estado.style().polish(self.estado)
        activo = est == "ACTIVO"
        for w in self.tabs_obj.values():
            w.aplicar_modo(self.modo, activo)
            w.cargar()
        for i in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(i, activo)

    @guarded
    def guardar(self, *_):
        v = self.form.values()
        ctx = self.app.ctx()
        if self.pmc:
            padron.modificar_contribuyente(ctx, self.pmc, v, self.modo, self.nro_orden)
        else:
            self.pmc = padron.nuevo_contribuyente(ctx, v, self.nro_orden)
        c = self.app.db.one("SELECT estado FROM contribuyentes WHERE pmc=?", (self.pmc,))
        self._refresh()
        if c["estado"] != "ACTIVO":
            falt = padron.faltantes_contribuyente(self.app.db.one("SELECT * FROM contribuyentes WHERE pmc=?", (self.pmc,)))
            info(self, "Registro guardado como INCOMPLETO. Falta: " + ", ".join(falt))
        else:
            info(self, f"Contribuyente guardado (PMC {self.pmc}). Ya puede registrar sus inmuebles, vehículos y actividades.")

    @guarded
    def kardex(self, *_):
        if not self.pmc:
            raise ServiceError("Primero guarde el contribuyente.")
        from ..core.paths import reports_dir
        p = reports_dir() / f"kardex_{self.pmc}.pdf"
        FM.generar(self.app.ctx(), FM.spec_kardex(self.app.ctx(), self.pmc), p)
        open_file(p)


class PmcPicker(QDialog):
    """Pantalla multiacceso (equivalente a F6)."""

    def __init__(self, app, parent=None, solo_con=None):
        super().__init__(parent)
        self.app, self.solo_con, self.pmc = app, solo_con, None
        self.setWindowTitle("Búsqueda de contribuyente (multiacceso)")
        self.resize(900, 520)
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        self.por = QComboBox()
        for k, v in (("nombre", "Apellido / nombre"), ("razon", "Razón social"), ("documento", "Documento / NIT"), ("pmc", "N° PMC"), ("placa", "Placa")):
            self.por.addItem(v, k)
        self.txt = QLineEdit()
        self.txt.setPlaceholderText("Escriba parte del texto y presione Enter (vacío = todos)")
        self.txt.returnPressed.connect(self.buscar)
        h.addWidget(self.por); h.addWidget(self.txt, 1); h.addWidget(btn("Buscar", self.buscar, primary=True))
        l.addLayout(h)
        self.t = DataTable(TABLA_PADRON)
        self.t.doble_click.connect(lambda *_: self.ok())
        l.addWidget(self.t)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.ok); bb.rejected.connect(self.reject)
        l.addWidget(bb)
        self.buscar()
        self.txt.setFocus()

    def buscar(self, *_):
        rows = padron.buscar(self.app.db, self.txt.text(), self.por.currentData(), 300, self.solo_con)
        self.t.set_data([dict(r, nombre=padron.nombre_completo(r)) for r in rows])

    def ok(self):
        r = self.t.current_row()
        if r:
            self.pmc = r["pmc"]
            self.accept()


TABLA_PADRON = [Col("pmc", "PMC"), Col("nombre", "Nombre / Razón social", "text", 3), Col("persona", "Tipo"), Col("nro_doc", "Documento"), Col("nit", "NIT"), Col("zona", "Zona"), Col("calle", "Calle", "text", 2), Col("estado", "Estado")]


def elegir_pmc(app, parent=None, solo_con=None):
    d = PmcPicker(app, parent, solo_con)
    return d.pmc if d.exec() == QDialog.Accepted else None


class PadronPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("page")
        l = QVBoxLayout(self)
        l.addWidget(titulo("Padrón Municipal de Contribuyentes (PMC)", "Altas (F-019), modificaciones e incorporaciones (F-027) y bajas (F-035). Búsqueda multiacceso por nombre, documento, PMC o placa."))
        h = QHBoxLayout()
        self.por = QComboBox()
        for k, v in (("nombre", "Apellido / nombre"), ("razon", "Razón social"), ("documento", "Documento / NIT"), ("pmc", "N° PMC"), ("placa", "Placa")):
            self.por.addItem(v, k)
        self.txt = QLineEdit()
        self.txt.setPlaceholderText("Buscar… (Enter)")
        self.txt.returnPressed.connect(self.cargar)
        h.addWidget(self.por); h.addWidget(self.txt, 1); h.addWidget(btn("Buscar", self.cargar, primary=True))
        l.addLayout(h)
        h2 = QHBoxLayout()
        for t, s, p in (("Nuevo contribuyente (F-019)", self.f019, True), ("Modificar / incorporar (F-027)", self.f027, False), ("Dar de baja bienes (F-035)", self.f035, False), ("Kardex PDF", self.kardex, False),
                        ("Cuenta corriente", self.cuenta, False), ("Certificado de solvencia", self.solvencia, False)):
            h2.addWidget(btn(t, s, primary=p))
        h2.addStretch(1)
        l.addLayout(h2)
        self.t = DataTable(TABLA_PADRON)
        self.t.doble_click.connect(lambda *_: self.f027())
        l.addWidget(self.t)
        self.lbl = QLabel()
        self.lbl.setObjectName("subtitulo")
        l.addWidget(self.lbl)
        self.cargar()

    def showEvent(self, e):
        super().showEvent(e)
        self.cargar()

    @guarded
    def cargar(self, *_):
        rows = padron.buscar(self.app.db, self.txt.text(), self.por.currentData(), 500)
        self.t.set_data([dict(r, nombre=padron.nombre_completo(r)) for r in rows])
        e = padron.estadisticas(self.app.db)
        self.lbl.setText(f"{len(rows)} resultado(s) · Padrón: {e['contribuyentes']} contribuyentes · {e['inmuebles']} inmuebles · {e['vehiculos']} vehículos · {e['actividades']} actividades · {e['incompletos']} incompletos")

    def _respaldo(self, modo, con_pmc):
        fields = [F("fecha", "Fecha de presentación de la DDJJ", "date", required=True), F("nro_orden", f"N° de orden preimpreso del {modo}", required=True)]
        if con_pmc:
            r = self.t.current_row()
            fields.insert(0, F("pmc", "N° PMC", "int", default=r["pmc"] if r else 0, lo=0, hi=99999999, required=True))
        return CrudDialog.ask(f"Documentación de respaldo {modo}", fields, parent=self)

    @guarded
    def f019(self, *_):
        self.app.session.can("padron.editar") or self._deny()
        v = self._respaldo("F-019", False)
        if v:
            d = ContribuyenteDialog(self.app, "F-019", None, v["nro_orden"], self)
            d.exec()
            self.cargar()

    def _deny(self):
        raise ServiceError("Su rol no permite editar el padrón.")

    def _con_pmc(self, modo, perm):
        self.app.session.can(perm) or self._deny()
        v = self._respaldo(modo, True)
        if v:
            if not self.app.db.one("SELECT 1 FROM contribuyentes WHERE pmc=?", (v["pmc"],)):
                raise ServiceError(f"El PMC {v['pmc']} no existe.")
            ContribuyenteDialog(self.app, modo, v["pmc"], v["nro_orden"], self).exec()
            self.cargar()

    @guarded
    def f027(self, *_):
        self._con_pmc("F-027", "padron.editar")

    @guarded
    def f035(self, *_):
        self._con_pmc("F-035", "padron.baja")

    def _sel(self):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un contribuyente.")
        return r["pmc"]

    @guarded
    def kardex(self, *_):
        pmc = self._sel()
        from ..core.paths import reports_dir
        p = reports_dir() / f"kardex_{pmc}.pdf"
        FM.generar(self.app.ctx(), FM.spec_kardex(self.app.ctx(), pmc), p)
        open_file(p)

    @guarded
    def cuenta(self, *_):
        from ..reports import catalogo, engine
        from ..core.paths import reports_dir
        pmc = self._sel()
        r = catalogo.ejecutar(self.app.ctx(), "rec_cuenta_corriente", pmc=pmc)
        p = reports_dir() / f"cuenta_{pmc}.pdf"
        engine.to_pdf(r, p, self.app.db.param("municipio"), self.app.session.usuario)
        open_file(p)

    @guarded
    def solvencia(self, *_):
        pmc = self._sel()
        from ..core.paths import reports_dir
        p = reports_dir() / f"solvencia_{pmc}.pdf"
        FM.generar(self.app.ctx(), FM.spec_solvencia(self.app.ctx(), pmc), p)
        open_file(p)
