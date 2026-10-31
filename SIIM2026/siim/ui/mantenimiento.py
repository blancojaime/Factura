"""Mantenimiento: editor genérico de tablas (zonas, barrios, rubros, tablas base de impuestos y patentes, etc.), usuarios y parámetros."""
import csv
from datetime import date

from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel, QTabWidget, QVBoxLayout, QWidget)

from ..core import security
from ..core.seed import (CALIDADES_CASA, CALIDADES_DEPTO, EXENCIONES, MATERIALES, PROCEDENCIAS, TIPOS_PUBLICIDAD)
from ..reports.engine import Col
from ..services.base import ServiceError
from .widgets import CrudDialog, DataTable, Field, FormPanel, btn, confirm, error, guarded, info, titulo

F = Field
GEST = lambda d=None: F("gestion", "Gestión", "int", default=d or date.today().year, lo=1990, hi=2100, required=True)

# Especificación de cada tabla editable: cols = (campo, etiqueta, tipo, choices) ; pk = campos clave; gestion = tiene columna gestión
TABLAS = {
    "cotizaciones": dict(titulo="Cotización del dólar y UFV", tabla="cotizaciones", pk=["fecha"], orden="fecha DESC", limite=400,
                         campos=[F("fecha", "Fecha", "date", required=True), F("tipo_dia", "Tipo de día", "choice", ["HABIL", "FERIADO"]), F("dolar", "Dólar (Bs)", "float", decimals=4, lo=0.01, required=True), F("ufv", "UFV (Bs)", "float", decimals=5, lo=0.01, required=True)],
                         ayuda="Registre diariamente la cotización oficial (BCB). Los feriados se usan para contar los 10 días hábiles del IMT. Puede importar un archivo CSV/Excel."),
    "tasas_interes": dict(titulo="Tasa de interés (r) para la Deuda Tributaria", tabla="tasas_interes", pk=["desde"], orden="desde DESC",
                          campos=[F("desde", "Vigente desde", "date", required=True), F("r", "Tasa anual r (ej. 0,1082 = 10,82 %)", "float", decimals=5, lo=0, hi=5, required=True)],
                          ayuda="r = tasa activa promedio para operaciones en UFV publicada por el BCB, incrementada en 3 puntos (Art. 47 Ley 2492)."),
    "zonas": dict(titulo="Zonas identificadas", tabla="zonas", pk=["codigo"], orden="codigo", campos=[F("codigo", "Código", "text", required=True, maxlen=6), F("descripcion", "Descripción", "text", required=True)]),
    "barrios": dict(titulo="Barrios y urbanizaciones", tabla="barrios", pk=["codigo"], orden="codigo",
                    campos=[F("codigo", "Código", "text", required=True, maxlen=8), F("descripcion", "Descripción", "text", required=True), F("zona", "Zona", "choice", "SQL:SELECT codigo, codigo||' – '||descripcion FROM zonas ORDER BY 1")]),
    "act_tipos": dict(titulo="Tipos de actividad económica", tabla="act_tipos", pk=["codigo"], orden="codigo", campos=[F("codigo", "Código", "text", required=True, maxlen=3), F("descripcion", "Descripción", "text", required=True)],
                      ayuda="Estructura definida en la Ordenanza de Patentes del municipio (el SIIM original tenía 15 tipos fijos; aquí puede adecuarse a su ley municipal)."),
    "act_categorias": dict(titulo="Categorías por actividad", tabla="act_categorias", pk=["act", "cat"], orden="act, cat", limite=2000,
                           campos=[F("act", "Actividad", "choice", "SQL:SELECT codigo, codigo||' – '||substr(descripcion,1,50) FROM act_tipos ORDER BY 1", required=True), F("cat", "Categoría", "text", required=True, maxlen=3), F("descripcion", "Descripción", "text", required=True)]),
    "ciiu": dict(titulo="Clasificador CIIU / CAEB", tabla="ciiu", pk=["codigo"], orden="codigo", limite=2000, campos=[F("codigo", "Código", "text", required=True, maxlen=8), F("descripcion", "Descripción", "text", required=True), F("es_detalle", "Es de detalle", "bool")]),
    "rubros": dict(titulo="Catálogo de rubros (clasificador de recursos)", tabla="rubros", pk=["codigo"], orden="codigo",
                   campos=[F("codigo", "Código (5 dígitos)", "text", required=True, maxlen=5), F("descripcion", "Descripción", "text", required=True), F("tipo", "Tipo", "choice", [("N", "N – Agregación"), ("S", "S – Entrada")]), F("permite_subniveles", "Permite subniveles", "bool")]),
    "subniveles": dict(titulo="Subniveles de recaudación (tasas, derechos, patentes eventuales, alquileres…)", tabla="subniveles", pk=["codigo"], orden="codigo", limite=3000,
                       campos=[F("codigo", "Código", "text", required=True, maxlen=10), F("rubro", "Rubro", "choice", "SQL:SELECT codigo, codigo||' – '||substr(descripcion,1,45) FROM rubros WHERE permite_subniveles=1 ORDER BY 1", required=True),
                               F("padre", "Subnivel padre (agregación)", "choice", "SQL:SELECT '', '(ninguno)' UNION ALL SELECT codigo, codigo||' – '||substr(descripcion,1,40) FROM subniveles WHERE tipo='AGREGACION'"),
                               F("descripcion", "Descripción", "text", required=True), F("tipo", "Tipo", "choice", ["ENTRADA", "AGREGACION", "INDIVIDUAL"]), F("frecuencia", "Frecuencia de cobro", "choice", ["EVENTUAL", "MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL"]),
                               F("monto", "Monto Bs (o 0 si usa %)", "float"), F("porcentaje", "Porcentaje % (o 0 si usa monto)", "float"), F("documento", "Documento de respaldo (ordenanza/ley)", "text"), F("activo", "Activo", "bool", default=True)],
                       ayuda="Elija monto fijo o porcentaje, no ambos. Códigos sugeridos: 5 dígitos del rubro + 2 de agregación + 3 de entrada."),
    "fechas_venc": dict(titulo="Fechas de vencimiento por rubro y gestión", tabla="fechas_venc", pk=["rubro", "gestion"], orden="gestion DESC, rubro",
                        campos=[F("rubro", "Rubro", "choice", ["IPBI", "IPVA", "PAF"], required=True), GEST(), F("contado", "Pago al contado (con 10 % desc.) hasta", "date", required=True), F("cuota1", "1.ª cuota hasta", "date?"), F("cuota2", "2.ª cuota hasta", "date?"),
                                F("sin_accesorios", "Sin descuento ni accesorios hasta", "date?")],
                        ayuda="Fechas fijadas por Resolución (IPBI/IPVA) o por la Ley Municipal de Patentes (PAF). 'Sin descuento ni accesorios' es el plazo de gracia previo a la mora."),
    # --- tablas base por gestión
    "tb_param": dict(titulo="Factores y parámetros por gestión (inclinación, servicios, alícuota rural, ajustes de vehículos)", tabla="tb_param", pk=["gestion", "clave"], gestion=True, orden="gestion DESC, clave",
                     campos=[GEST(), F("clave", "Parámetro", "choice", ["inc_plano", "inc_inclinado", "inc_muy", "serv_minimo", "serv_luz", "serv_agua", "serv_alcant", "serv_telef", "ipbi_rural_alicuota", "veh_deduc_2puertas", "veh_incr_turbo", "veh_incr_doble_tr"], required=True), F("valor", "Valor", "float", decimals=4, hi=1e9)]),
    "tb_material_via": dict(titulo="IPBI – Material en vías por zona (valor por m²)", tabla="tb_material_via", pk=["gestion", "zona", "material"], gestion=True, orden="gestion DESC, zona, material", limite=3000,
                            campos=[GEST(), F("zona", "Zona", "choice", "SQL:SELECT codigo, codigo||' – '||descripcion FROM zonas ORDER BY 1", required=True), F("material", "Material", "choice", MATERIALES, required=True), F("valor", "Valor Bs/m²", "float", hi=1e9)]),
    "tb_calidad_const": dict(titulo="IPBI – Valor de la construcción por calidad", tabla="tb_calidad_const", pk=["gestion", "tipo", "calidad"], gestion=True, orden="gestion DESC, tipo, valor_m2 DESC",
                             campos=[GEST(), F("tipo", "Tipo", "choice", ["CASA", "DEPARTAMENTO"], required=True), F("calidad", "Calidad", "choice", sorted(set(CALIDADES_CASA + CALIDADES_DEPTO)), required=True), F("valor_m2", "Valor Bs/m²", "float", hi=1e9)]),
    "tb_deprec_inm": dict(titulo="IPBI – Depreciación de construcciones (por antigüedad)", tabla="tb_deprec_inm", pk=["gestion", "desde"], gestion=True, orden="gestion DESC, desde",
                          campos=[GEST(), F("desde", "Años desde", "int", required=True), F("hasta", "Años hasta", "int", hi=999), F("factor", "Factor", "float", decimals=3, hi=1)]),
    "tb_escala_inm": dict(titulo="IPBI – Escala impositiva (cuota fija + % sobre excedente)", tabla="tb_escala_inm", pk=["gestion", "orden"], gestion=True, orden="gestion DESC, orden",
                          campos=[GEST(), F("orden", "N° de tramo", "int", lo=1, required=True), F("desde", "Desde Bs", "float", hi=1e12), F("hasta", "Hasta Bs", "float", hi=1e12), F("cuota_fija", "Cuota fija Bs", "float", hi=1e12), F("porcentaje", "Más %", "float", decimals=3), F("excedente", "Sobre el excedente de Bs", "float", hi=1e12)]),
    "tb_veh_cilindrada": dict(titulo="IPVA – Rangos de cilindrada (código)", tabla="tb_veh_cilindrada", pk=["gestion", "codigo", "moto"], gestion=True, orden="gestion DESC, moto, codigo", limite=2000,
                              campos=[GEST(), F("codigo", "Código", "int", required=True), F("desde", "Desde cc", "int", hi=99999), F("hasta", "Hasta cc", "int", hi=99999), F("moto", "Motocicletas", "bool")]),
    "tb_veh_valor": dict(titulo="IPVA – Valor por cilindrada y procedencia", tabla="tb_veh_valor", pk=["gestion", "codigo", "procedencia"], gestion=True, orden="gestion DESC, codigo, procedencia", limite=3000,
                         campos=[GEST(), F("codigo", "Código cilindrada", "int", required=True), F("procedencia", "Procedencia", "choice", PROCEDENCIAS, required=True), F("valor", "Valor Bs", "float", hi=1e12)]),
    "tb_moto_valor": dict(titulo="IPVA – Valor de motocicletas, motonetas y cuadratracks", tabla="tb_moto_valor", pk=["gestion", "codigo"], gestion=True, orden="gestion DESC, codigo",
                          campos=[GEST(), F("codigo", "Código cilindrada", "int", required=True), F("valor", "Valor Bs", "float", hi=1e12)]),
    "tb_veh_deprec": dict(titulo="IPVA – Depreciación por antigüedad (0 = año de fabricación)", tabla="tb_veh_deprec", pk=["gestion", "antiguedad"], gestion=True, orden="gestion DESC, antiguedad",
                          campos=[GEST(), F("antiguedad", "Antigüedad (años)", "int", required=True), F("factor", "Factor", "float", decimals=3, hi=1)]),
    "tb_veh_escala": dict(titulo="IPVA – Escala impositiva", tabla="tb_veh_escala", pk=["gestion", "orden"], gestion=True, orden="gestion DESC, orden",
                          campos=[GEST(), F("orden", "N° de tramo", "int", lo=1, required=True), F("desde", "Desde Bs", "float", hi=1e12), F("hasta", "Hasta Bs", "float", hi=1e12), F("cuota_fija", "Cuota fija Bs", "float", hi=1e12), F("porcentaje", "Más %", "float", decimals=3), F("excedente", "Sobre el excedente de Bs", "float", hi=1e12)]),
    "tb_veh_correccion": dict(titulo="IPVA – Factores de corrección por chasis y carrocería (> 1,5 t)", tabla="tb_veh_correccion", pk=["gestion", "tramo"], gestion=True, orden="gestion DESC, tramo",
                              campos=[GEST(), F("tramo", "Tramo", "int", lo=1, required=True), F("hasta_ton", "Hasta toneladas", "float"), F("chasis_torpedo", "Chasis torpedo", "float"), F("chasis_cabinado", "Chasis cabinado", "float"), F("carr_estacas", "Carr. estacas", "float"),
                                      F("carr_micros", "Carr. micros", "float"), F("carr_buses", "Carr. buses", "float"), F("carr_otros", "Carr. otros", "float")]),
    "tb_act_tope": dict(titulo="PATENTES – Topes máximos anuales (PMA) y montos fijos por actividad y categoría", tabla="tb_act_tope", pk=["gestion", "act", "cat"], gestion=True, orden="gestion DESC, act, cat", limite=5000,
                        campos=[GEST(), F("act", "Actividad", "choice", "SQL:SELECT codigo, codigo||' – '||substr(descripcion,1,50) FROM act_tipos ORDER BY 1", required=True), F("cat", "Categoría", "text", required=True, maxlen=3),
                                F("tope", "Patente máxima anual (Bs)", "float", hi=1e12), F("fijo", "Monto fijo (modalidad categoría) Bs", "float", hi=1e12)],
                        ayuda="Valores establecidos en la Ley Municipal de Patentes vigente. PMA se usa en modalidad Tope×Zona-Superficie; 'fijo' en modalidad Categoría."),
    "tb_act_zona_sup": dict(titulo="PATENTES – Porcentaje según zona y superficie", tabla="tb_act_zona_sup", pk=["gestion", "zona", "desde"], gestion=True, orden="gestion DESC, zona, desde", limite=3000,
                            campos=[GEST(), F("zona", "Zona", "choice", "SQL:SELECT codigo, codigo||' – '||descripcion FROM zonas ORDER BY 1", required=True), F("desde", "Desde m²", "float", hi=1e9), F("hasta", "Hasta m²", "float", hi=1e12), F("porcentaje", "Porcentaje %", "float", hi=1000)]),
    "tb_act_pua": dict(titulo="PATENTES – Patente Única Anual: valor por m² y zona", tabla="tb_act_pua", pk=["gestion", "zona"], gestion=True, orden="gestion DESC, zona",
                       campos=[GEST(), F("zona", "Zona", "choice", "SQL:SELECT codigo, codigo||' – '||descripcion FROM zonas ORDER BY 1", required=True), F("valor_m2", "Valor Bs/m²", "float", hi=1e9)]),
    "tb_act_consumo": dict(titulo="PATENTES – Factor por consumo eléctrico (opcional)", tabla="tb_act_consumo", pk=["gestion", "desde"], gestion=True, orden="gestion DESC, desde",
                           campos=[GEST(), F("desde", "Desde kWh/mes", "float", hi=1e9), F("hasta", "Hasta kWh/mes", "float", hi=1e12), F("factor", "Factor multiplicador", "float", decimals=3, hi=100)]),
    "tb_publicidad": dict(titulo="PATENTES – Publicidad y propaganda: arancel por m² anual", tabla="tb_publicidad", pk=["gestion", "tipo"], gestion=True, orden="gestion DESC, tipo",
                          campos=[GEST(), F("tipo", "Tipo de anuncio", "choice", TIPOS_PUBLICIDAD, required=True), F("valor_m2", "Bs por m² anual", "float", hi=1e9)]),
}

GRUPOS = [("Generales", ["cotizaciones", "tasas_interes", "zonas", "barrios", "fechas_venc"]),
          ("Actividades y rubros", ["act_tipos", "act_categorias", "ciiu", "rubros", "subniveles"]),
          ("Tablas IPBI", ["tb_param", "tb_material_via", "tb_calidad_const", "tb_deprec_inm", "tb_escala_inm"]),
          ("Tablas IPVA", ["tb_veh_cilindrada", "tb_veh_valor", "tb_moto_valor", "tb_veh_deprec", "tb_veh_escala", "tb_veh_correccion"]),
          ("Tablas Patentes", ["tb_act_tope", "tb_act_zona_sup", "tb_act_pua", "tb_act_consumo", "tb_publicidad"])]


def _fields_resolved(db, campos):
    out = []
    for f in campos:
        if f.kind == "choice" and isinstance(f.choices, str) and f.choices.startswith("SQL:"):
            f = Field(f.name, f.label, "choice", [(r[0], r[1]) for r in db.all(f.choices[4:])], f.default, f.required)
        out.append(f)
    return out


class TableEditor(QWidget):
    def __init__(self, app, key, parent=None):
        super().__init__(parent)
        self.app, self.key, self.spec = app, key, TABLAS[key]
        self.setObjectName("page")
        lay = QVBoxLayout(self)
        lay.addWidget(titulo(self.spec["titulo"], self.spec.get("ayuda", "")))
        bar = QHBoxLayout()
        self.filtro = None
        if self.spec.get("gestion"):
            self.filtro = QComboBox()
            self.filtro.currentIndexChanged.connect(self.cargar)
            bar.addWidget(QLabel("Gestión:"))
            bar.addWidget(self.filtro)
        bar.addWidget(btn("Insertar", self.nuevo, primary=True))
        bar.addWidget(btn("Modificar", self.editar))
        bar.addWidget(btn("Eliminar", self.eliminar, danger=True))
        if self.spec.get("gestion"):
            bar.addWidget(btn("Copiar a otra gestión…", self.copiar))
        bar.addWidget(btn("Importar CSV/Excel…", self.importar))
        bar.addStretch(1)
        lay.addLayout(bar)
        self.tabla = DataTable([Col(f.name, f.label, "money" if f.kind == "float" else "text") for f in self.spec["campos"]])
        self.tabla.doble_click.connect(lambda *_: self.editar())
        lay.addWidget(self.tabla)
        self.cargar()

    def ctx(self):
        return self.app.ctx()

    def cargar(self, *_):
        db = self.app.db
        if self.filtro is not None and self.filtro.count() == 0:
            gs = [r[0] for r in db.all(f"SELECT DISTINCT gestion FROM {self.spec['tabla']} ORDER BY gestion DESC")] or [date.today().year]
            self.filtro.blockSignals(True)
            for g in gs:
                self.filtro.addItem(str(g), g)
            self.filtro.blockSignals(False)
        q = f"SELECT * FROM {self.spec['tabla']}"
        a = []
        if self.filtro is not None and self.filtro.currentData() is not None:
            q += " WHERE gestion=?"; a.append(self.filtro.currentData())
        q += f" ORDER BY {self.spec['orden']} LIMIT {self.spec.get('limite', 1000)}"
        cols = []
        for f in self.spec["campos"]:
            k = "money" if f.kind == "float" else "text"
            if f.kind == "date" or f.kind == "date?":
                k = "date"
            cols.append(Col(f.name, f.label, k))
        self.tabla.set_cols(cols)
        self.tabla.set_data(db.all(q, a))

    @guarded
    def nuevo(self, *_):
        self._dlg(None)

    @guarded
    def editar(self, *_):
        r = self.tabla.current_row()
        if not r:
            raise ServiceError("Seleccione un registro.")
        self._dlg(r)

    def _dlg(self, row):
        self.app.session.can("mant.editar") or self._deny()
        fields = _fields_resolved(self.app.db, self.spec["campos"])
        vals = row
        if row is None and self.filtro is not None and self.filtro.currentData():
            vals = {"gestion": self.filtro.currentData()}
        v = CrudDialog.ask(("Modificar" if row else "Insertar") + " – " + self.spec["titulo"][:60], fields, vals, self, columns=1 if len(fields) < 7 else 2, width=520 if len(fields) < 7 else 800)
        if v is None:
            return
        db = self.app.db
        pk = self.spec["pk"]
        with db.tx():
            if row and any(str(row[k]) != str(v[k]) for k in pk):
                db.execute(f"DELETE FROM {self.spec['tabla']} WHERE " + " AND ".join(f"{k}=?" for k in pk), [row[k] for k in pk])
            cols = ",".join(v)
            db.execute(f"INSERT OR REPLACE INTO {self.spec['tabla']}({cols}) VALUES({','.join('?' * len(v))})", list(v.values()))
            self.ctx().log("MANT_" + ("MODIF" if row else "ALTA"), self.spec["tabla"], "/".join(str(v[k]) for k in pk), v)
        self.filtro.clear() if self.filtro is not None else None
        self.cargar()

    def _deny(self):
        raise ServiceError("Su rol no permite modificar las tablas de mantenimiento.")

    @guarded
    def eliminar(self, *_):
        self.app.session.can("mant.editar") or self._deny()
        r = self.tabla.current_row()
        if not r:
            raise ServiceError("Seleccione un registro.")
        if not confirm(self, "¿Eliminar el registro seleccionado?"):
            return
        pk = self.spec["pk"]
        try:
            self.app.db.execute(f"DELETE FROM {self.spec['tabla']} WHERE " + " AND ".join(f"{k}=?" for k in pk), [r[k] for k in pk])
        except Exception as e:
            raise ServiceError(f"No se puede eliminar: el registro está en uso ({e}).")
        self.ctx().log("MANT_BAJA", self.spec["tabla"], "/".join(str(r[k]) for k in pk))
        self.cargar()

    @guarded
    def copiar(self, *_):
        self.app.session.can("mant.editar") or self._deny()
        g0 = self.filtro.currentData()
        v = CrudDialog.ask("Copiar tabla a otra gestión", [Field("g", "Gestión destino", "int", default=(g0 or date.today().year) + 1, lo=1990, hi=2100, required=True)], parent=self)
        if not v:
            return
        db = self.app.db
        cols = [f.name for f in self.spec["campos"]]
        with db.tx():
            for r in db.all(f"SELECT * FROM {self.spec['tabla']} WHERE gestion=?", (g0,)):
                d = {c: r[c] for c in cols}
                d["gestion"] = v["g"]
                db.execute(f"INSERT OR IGNORE INTO {self.spec['tabla']}({','.join(d)}) VALUES({','.join('?' * len(d))})", list(d.values()))
            self.ctx().log("MANT_COPIA_GESTION", self.spec["tabla"], f"{g0}->{v['g']}")
        self.filtro.clear()
        self.cargar()
        info(self, f"Tabla copiada a la gestión {v['g']}. Actualice los valores según la nueva resolución/ley.")

    @guarded
    def importar(self, *_):
        self.app.session.can("mant.editar") or self._deny()
        fn, _ = QFileDialog.getOpenFileName(self, "Importar", "", "Excel/CSV (*.xlsx *.csv)")
        if not fn:
            return
        filas = leer_tabla(fn)
        cols = [f.name for f in self.spec["campos"]]
        falt = [c for c in cols if c not in filas[0]] if filas else cols
        ok_cols = [c for c in cols if c in (filas[0] if filas else {})]
        pk = self.spec["pk"]
        if any(k not in ok_cols for k in pk):
            raise ServiceError("El archivo debe tener encabezados con los nombres de campo (primera fila): " + ", ".join(cols))
        db = self.app.db
        n = 0
        with db.tx():
            for r in filas:
                d = {c: (None if r[c] in ("", None) else r[c]) for c in ok_cols}
                db.execute(f"INSERT OR REPLACE INTO {self.spec['tabla']}({','.join(d)}) VALUES({','.join('?' * len(d))})", list(d.values()))
                n += 1
            self.ctx().log("MANT_IMPORTA", self.spec["tabla"], None, {"filas": n, "archivo": fn})
        if self.filtro is not None:
            self.filtro.clear()
        self.cargar()
        info(self, f"{n} filas importadas." + (f"\nColumnas no presentes (quedan por defecto): {', '.join(falt)}" if falt else ""))


def leer_tabla(path):
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8-sig") as f:
            sample = f.read(2048); f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample else csv.excel
            return [dict(r) for r in csv.DictReader(f, dialect=dialect)]
    from openpyxl import load_workbook
    ws = load_workbook(path, read_only=True, data_only=True).active
    it = ws.iter_rows(values_only=True)
    head = [str(h).strip() if h is not None else "" for h in next(it)]
    out = []
    for row in it:
        if all(v is None for v in row):
            continue
        out.append({h: (v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else v) for h, v in zip(head, row)})
    return out


class UsuariosPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("page")
        lay = QVBoxLayout(self)
        lay.addWidget(titulo("Usuarios del sistema", "Cada usuario tiene un rol con permisos distintos. Las contraseñas se almacenan cifradas (PBKDF2) y toda operación queda en la bitácora."))
        bar = QHBoxLayout()
        for t, s, p in (("Nuevo usuario", self.nuevo, True), ("Modificar", self.editar, False), ("Restablecer clave", self.reset, False), ("Activar / desactivar", self.toggle, False)):
            bar.addWidget(btn(t, s, primary=p))
        bar.addStretch(1)
        lay.addLayout(bar)
        self.t = DataTable([Col("usuario", "Usuario"), Col("nombre", "Nombre", "text", 2), Col("rol", "Rol"), Col("activo", "Activo", "int"), Col("ultimo_acceso", "Último acceso")])
        lay.addWidget(self.t)
        self.cargar()

    def cargar(self):
        self.t.set_data(self.app.db.all("SELECT * FROM usuarios ORDER BY usuario"))

    def _req(self):
        if self.app.session.rol != "ADMINISTRADOR":
            raise ServiceError("Sólo el administrador gestiona usuarios.")

    @guarded
    def nuevo(self, *_):
        self._req()
        v = CrudDialog.ask("Nuevo usuario", [Field("usuario", "Usuario", required=True, maxlen=20), Field("nombre", "Nombre completo", required=True), Field("rol", "Rol", "choice", list(security.ROLES), default="CAJERO"),
                                             Field("clave", "Contraseña inicial", required=True, tip="Mínimo 8 caracteres con letras y números")], parent=self)
        if v:
            security.create_user(self.app.db, v["usuario"], v["nombre"], v["rol"], v["clave"], cambiar_clave=True)
            self.app.ctx().log("USUARIO_ALTA", "usuarios", v["usuario"], {"rol": v["rol"]})
            self.cargar()

    @guarded
    def editar(self, *_):
        self._req()
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un usuario.")
        v = CrudDialog.ask("Modificar usuario", [Field("nombre", "Nombre completo", required=True), Field("rol", "Rol", "choice", list(security.ROLES))], r, self)
        if v:
            if r["usuario"] == self.app.session.usuario and v["rol"] != "ADMINISTRADOR":
                raise ServiceError("No puede quitarse a sí mismo el rol de administrador.")
            self.app.db.update("usuarios", v, "id=?", (r["id"],))
            self.app.ctx().log("USUARIO_MODIF", "usuarios", r["usuario"], v)
            self.cargar()

    @guarded
    def reset(self, *_):
        self._req()
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un usuario.")
        v = CrudDialog.ask("Restablecer contraseña", [Field("clave", "Nueva contraseña", required=True)], parent=self)
        if v:
            security.change_password(self.app.db, r["usuario"], v["clave"])
            self.app.db.update("usuarios", {"cambiar_clave": 1}, "id=?", (r["id"],))
            info(self, "Contraseña restablecida. El usuario deberá cambiarla al ingresar.")

    @guarded
    def toggle(self, *_):
        self._req()
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un usuario.")
        if r["usuario"] == self.app.session.usuario:
            raise ServiceError("No puede desactivarse a sí mismo.")
        self.app.db.update("usuarios", {"activo": 0 if r["activo"] else 1}, "id=?", (r["id"],))
        self.app.ctx().log("USUARIO_ACTIVO", "usuarios", r["usuario"], {"activo": not r["activo"]})
        self.cargar()


PARAMS_FORM = [
    Field("municipio", "Gobierno Autónomo Municipal", required=True), Field("codigo_ine", "Código INE"), Field("departamento", "Departamento"), Field("direccion", "Dirección"), Field("telefono", "Teléfono"),
    Field("alcalde", "Alcalde(sa) Municipal"), Field("responsable_tributario", "Responsable de la Administración Tributaria"),
    Field("base_legal", "Base legal (ley municipal de patentes y tasas)", tip="Se imprime en los formularios. Ej.: Ley Municipal Nº 123/2026"),
    Field("gestion_desde", "Gestiones a liquidar: desde", "int", lo=1990, hi=2100), Field("gestion_hasta", "Gestiones a liquidar: hasta", "int", lo=1990, hi=2100),
    Field("descuento_contado", "Descuento por pago al contado (%)", "float"), Field("imt_alicuota", "Alícuota IMT (%)", "float"), Field("reposicion_formulario", "Costo de reposición de formulario (Bs)", "float"),
    Field("sancion_administrativa", "Sanción administrativa fija (Bs)", "float"), Field("persona_df_min_n", "Multa deberes formales mínima – natural (UFV)", "float"), Field("persona_df_min_j", "Multa deberes formales mínima – jurídica (UFV)", "float"),
    Field("df_max", "Multa deberes formales máxima (UFV)", "float"), Field("df_pct", "Multa deberes formales (% del tributo omitido)", "float"),
    Field("modo_df_ufv", "Cálculo de TO en UFV para la multa", "choice", [("DIVISION", "TO ÷ UFV (definición legal)"), ("SIIM_PDF", "TO × UFV (como en los Apuntes SIIM)")]),
    Field("redondeo_deuda", "Decimales en la Deuda Tributaria", "choice", [("0", "0 – bolivianos enteros"), ("2", "2 – centavos")]),
    Field("patente_modalidad", "Modalidad de cálculo de la Patente de Funcionamiento", "choice", [("TOPE_ZONA_SUP", "Patente máxima × % zona-superficie"), ("PUA", "Patente Única Anual (m² × valor zona)"), ("CATEGORIA", "Monto fijo por categoría")]),
    Field("patente_actualiza_dolar", "Actualizar patente por variación del dólar", "choice", [("0", "No"), ("1", "Sí")]), Field("patente_minima", "Patente mínima (Bs)", "float"),
    Field("licencia_vigencia_meses", "Vigencia de la licencia (meses)", "int", lo=1, hi=60), Field("alerta_licencia_dias", "Alertar licencias que vencen en (días)", "int", lo=1, hi=365),
    Field("plan_max_cuotas", "Plan de pagos: máximo de cuotas", "int", lo=1, hi=120), Field("plan_tasa_anual", "Plan de pagos: tasa anual (ej. 0,1082)", "float", decimals=4), Field("plan_cuota_inicial_pct", "Plan de pagos: cuota inicial (%)", "float"),
    Field("modalidad_recaudacion", "Modalidad de recaudación", "choice", [("CAJA", "Cajas municipales"), ("BANCO", "Entidades financieras"), ("MIXTA", "Mixta")]), Field("comision_bancaria", "Comisión bancaria (%)", "float", decimals=3),
    Field("sesion_minutos", "Cierre de sesión por inactividad (min)", "int", lo=5, hi=480), Field("prescripcion_anios", "Prescripción (años)", "int", lo=1, hi=10),
]


class ParametrosPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("page")
        lay = QVBoxLayout(self)
        lay.addWidget(titulo("Parámetros globales", "Personalice el sistema para su municipio. Estos valores se imprimen en formularios y rigen los cálculos."))
        from PySide6.QtWidgets import QScrollArea
        self.form = FormPanel(PARAMS_FORM, columns=2)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.form)
        lay.addWidget(sc)
        for f in PARAMS_FORM:
            v = app.db.param(f.name)
            if f.kind in ("int", "float"):
                v = float(v or 0)
            self.form.set(f.name, v)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(btn("Guardar parámetros", self.guardar, primary=True))
        lay.addLayout(h)

    @guarded
    def guardar(self, *_):
        if not self.app.session.can("mant.editar"):
            raise ServiceError("Su rol no permite modificar parámetros.")
        self.form.validate()
        v = self.form.values()
        if int(v["gestion_desde"]) > int(v["gestion_hasta"]):
            raise ServiceError("El rango de gestiones es inválido.")
        with self.app.db.tx():
            for k, x in v.items():
                self.app.db.set_param(k, "" if x is None else (int(x) if isinstance(x, float) and float(x).is_integer() else x))
            self.app.ctx().log("PARAMETROS", "parametros", None, v)
        info(self, "Parámetros guardados.")
        self.app.refrescar_estado()


CORTO = {"cotizaciones": "Dólar y UFV", "tasas_interes": "Tasa de interés", "fechas_venc": "Vencimientos", "act_tipos": "Tipos de actividad", "act_categorias": "Categorías", "ciiu": "CIIU / CAEB",
         "subniveles": "Subniveles", "rubros": "Rubros", "tb_param": "Factores", "tb_material_via": "Material en vías", "tb_calidad_const": "Calidad constr.", "tb_deprec_inm": "Depreciación",
         "tb_escala_inm": "Escala IPBI", "tb_veh_cilindrada": "Cilindrada", "tb_veh_valor": "Valores", "tb_moto_valor": "Motos", "tb_veh_deprec": "Depreciación", "tb_veh_escala": "Escala IPVA",
         "tb_veh_correccion": "Chasis/carrocería", "tb_act_tope": "Topes (PMA)", "tb_act_zona_sup": "Zona–superficie", "tb_act_pua": "PUA por m²", "tb_act_consumo": "Consumo eléctrico", "tb_publicidad": "Publicidad"}


class MantenimientoPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("page")
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        lay.addWidget(tabs)
        tabs.addTab(ParametrosPage(app), "Parámetros")
        tabs.addTab(UsuariosPage(app), "Usuarios")
        for nombre, keys in GRUPOS:
            sub = QTabWidget()
            sub.setUsesScrollButtons(True)
            for k in keys:
                sub.addTab(TableEditor(app, k), CORTO.get(k) or TABLAS[k]["titulo"].split(" – ")[-1].split("(")[0].strip()[:26])
            tabs.addTab(sub, nombre)
