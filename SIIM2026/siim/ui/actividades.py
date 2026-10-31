"""Módulo especial: Actividades Económicas, Tasas y Patentes. Licencias, alertas, simulador de patente, inspecciones y verificación."""
from datetime import date

from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QTabWidget, QTextEdit, QVBoxLayout, QWidget

from ..calc.ipbi import CalcError
from ..calc.patentes import MODALIDADES, calcular_paf
from ..core.paths import reports_dir
from ..reports import catalogo, engine
from ..reports import formularios as FM
from ..reports.engine import Col, fmt_num
from ..services import padron
from ..services.base import ServiceError, hoy
from .padron import ContribuyenteDialog, campos_objeto
from .widgets import CrudDialog, DataTable, ExportBar, Field, FormPanel, btn, confirm, guarded, info, open_file, titulo

F = Field


class Padron(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        self.q = CrudDialog("", [F("txt", "Buscar (establecimiento / titular)"), F("estado", "Licencia", "choice", ["", "VIGENTE", "VENCIDA", "SIN LICENCIA", "SUSPENDIDA", "CANCELADA"])], None, None)
        self.q.layout().removeWidget(self.q.form)
        h.addWidget(self.q.form, 1)
        h.addWidget(btn("Buscar", self.cargar, primary=True))
        l.addLayout(h)
        self.t = DataTable([Col("id", "ID", "int"), Col("pmc", "PMC"), Col("titular", "Titular", "text", 2), Col("nombre_comercial", "Establecimiento", "text", 2), Col("cod", "Act-Cat"), Col("zona", "Zona"), Col("nro_licencia", "N° licencia"), Col("licencia_vence", "Vence", "date"), Col("estado_licencia", "Licencia")])
        l.addWidget(self.t, 1)
        bar = QHBoxLayout()
        for tx, s, p in (("Emitir / renovar licencia", self.emitir, True), ("Imprimir licencia (QR)", self.imprimir, False), ("Registrar inspección", self.inspeccion, False), ("Abrir contribuyente (F-027)", self.abrir, False)):
            bar.addWidget(btn(tx, s, primary=p))
        bar.addStretch(1)
        l.addLayout(bar)
        self.cargar()

    def showEvent(self, e):
        super().showEvent(e)
        self.cargar()

    @guarded
    def cargar(self, *_):
        padron.refrescar_licencias(self.app.db)
        v = self.q.form.values()
        q = """SELECT a.*, a.act||'-'||a.cat AS cod, COALESCE(NULLIF(c.razon_social,''), TRIM(IFNULL(c.paterno,'')||' '||IFNULL(c.materno,'')||' '||IFNULL(c.nombre,''))) AS titular
               FROM actividades a JOIN contribuyentes c ON c.pmc=a.pmc WHERE a.estado='ACTIVO'"""
        a = []
        if v["txt"]:
            q += " AND (a.nombre_comercial LIKE ? OR c.paterno LIKE ? OR c.razon_social LIKE ?)"; a += [f"%{v['txt']}%"] * 3
        if v["estado"]:
            q += " AND a.estado_licencia=?"; a.append(v["estado"])
        self.t.set_data(self.app.db.all(q + " ORDER BY a.nombre_comercial LIMIT 800", a))

    def _sel(self):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione una actividad.")
        return r

    @guarded
    def emitir(self, *_):
        r = self._sel()
        try:
            nro, v = padron.emitir_licencia(self.app.ctx(), r["id"])
        except ServiceError as e:
            if "sin pagar" in str(e) and self.app.session.can("rec.anular") and confirm(self, str(e) + "\n\n¿Emitir de todos modos con autorización de supervisor?"):
                nro, v = padron.emitir_licencia(self.app.ctx(), r["id"], permitir_con_deuda=True)
            else:
                raise
        info(self, f"Licencia {nro} emitida, vigente hasta {v}.")
        self.cargar()

    @guarded
    def imprimir(self, *_):
        r = self._sel()
        p = reports_dir() / f"licencia_{r['id']}.pdf"
        FM.generar(self.app.ctx(), FM.spec_licencia(self.app.ctx(), r["id"]), p)
        open_file(p)

    @guarded
    def inspeccion(self, *_):
        r = self._sel()
        v = CrudDialog.ask("Inspección – " + (r["nombre_comercial"] or ""), [F("fecha", "Fecha", "date"), F("resultado", "Resultado", "choice", ["CONFORME", "OBSERVADO", "CLAUSURA"]), F("observaciones", "Observaciones", "area"), F("plazo", "Plazo para subsanar", "date?"), F("inspector", "Inspector")], parent=self, width=560)
        if v:
            padron.registrar_inspeccion(self.app.ctx(), r["id"], v["resultado"], v["observaciones"] or "", v["inspector"] or "", v["plazo"])
            self.cargar()

    @guarded
    def abrir(self, *_):
        r = self._sel()
        ContribuyenteDialog(self.app, "F-027", r["pmc"], "", self).exec()
        self.cargar()


class Alertas(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        l.addWidget(titulo("Alertas de fiscalización", "Licencias por vencer, vencidas o inexistentes, y proyección de ingresos."))
        h = QHBoxLayout()
        self.cb = QComboBox()
        for k, v in (("act_licencias_vencer", "Licencias que vencen en los próximos 30 días"), ("act_sin_licencia", "Sin licencia / vencidas / suspendidas"), ("act_resumen_tipo", "Resumen por tipo de actividad"), ("act_ciiu", "Por clasificador CIIU"), ("act_inspecciones", "Inspecciones realizadas")):
            self.cb.addItem(v, k)
        h.addWidget(self.cb, 1); h.addWidget(btn("Mostrar", self.cargar, primary=True))
        l.addLayout(h)
        self.t = DataTable([])
        l.addWidget(self.t, 1)
        self.rep = None
        l.addWidget(ExportBar(lambda: self.rep or self.cargar(), app.ctx))
        self.cargar()

    @guarded
    def cargar(self, *_):
        self.rep = catalogo.ejecutar(self.app.ctx(), self.cb.currentData())
        self.t.set_cols(self.rep.cols)
        self.t.set_data(self.rep.rows)
        return self.rep


class Simulador(QWidget):
    """Compara las tres modalidades de cálculo de patente para un establecimiento real o hipotético (apoyo al diseño de la ordenanza)."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        l.addWidget(titulo("Simulador de Patente de Funcionamiento", "Ingrese los datos de un establecimiento (real o hipotético) y compare el importe según cada modalidad de cálculo. Útil para analizar el impacto de una nueva ley municipal de patentes."))
        fields = campos_objeto(app.db, "actividades")
        keep = {"act", "cat", "zona", "superficie", "consumo_elect", "fecha_inicio", "fecha_cese"}
        fs = [f for f in fields if f.name in keep]
        fs.append(F("gestion", "Gestión", "int", lo=1990, hi=2100, default=int(app.db.param("gestion_hasta"))))
        self.form = FormPanel(fs, columns=2)
        self.form.w["act"].currentIndexChanged.connect(self._cats)
        self._cats()
        l.addWidget(self.form)
        l.addWidget(btn("Simular", self.simular, primary=True))
        self.t = DataTable([Col("mod", "Modalidad", "text", 2), Col("det", "Detalle", "text", 3), Col("imp", "Patente anual Bs", "money")])
        l.addWidget(self.t, 1)

    def _cats(self, *_):
        a = self.form.get("act")
        self.form.set_choices("cat", [(r[0], f"{r[0]} – {r[1][:60]}") for r in self.app.db.all("SELECT cat, descripcion FROM act_categorias WHERE act=? ORDER BY cat", (a,))], keep=False)

    @guarded
    def simular(self, *_):
        v = self.form.values()
        act = dict(v, exento="NINGUNO", nombre_comercial="Simulación")
        rows = []
        for m, desc in MODALIDADES.items():
            try:
                d = calcular_paf(self.app.db, act, int(v["gestion"]), m)
                det = ", ".join(f"{k}={x}" for k, x in d.items() if k not in ("gestion", "modalidad", "base_imponible", "impuesto"))
                rows.append(dict(mod=f"{m} – {desc}", det=det, imp=d["impuesto"]))
            except CalcError as e:
                rows.append(dict(mod=f"{m} – {desc}", det=str(e), imp=None))
        self.t.set_data(rows)


class Verificar(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        l.addWidget(titulo("Verificar autenticidad de una licencia", "Ingrese el número y el código de verificación impresos (o leídos del QR)."))
        self.f = CrudDialog("", [F("nro", "N° de licencia", required=True), F("sello", "Código de verificación", required=True)], None, None)
        self.f.layout().removeWidget(self.f.form)
        l.addWidget(self.f.form)
        l.addWidget(btn("Verificar", self.ver, primary=True))
        self.res = QLabel("")
        self.res.setObjectName("titulo")
        self.res.setWordWrap(True)
        l.addWidget(self.res)
        l.addStretch(1)

    @guarded
    def ver(self, *_):
        self.f.form.validate()
        v = self.f.form.values()
        r = FM.verificar_licencia(self.app.db, v["nro"], v["sello"])
        if r["valida"]:
            self.res.setText(f"{'✔ AUTÉNTICA Y VIGENTE' if r['vigente'] else '✔ Auténtica pero NO vigente'}\n{r['establecimiento']} – PMC {r['pmc']}\nEstado: {r['estado']} · Vence: {r['vence']}")
            self.res.setObjectName("ok" if r["vigente"] else "warn")
        else:
            self.res.setText("✖ NO VÁLIDA: " + r["motivo"])
            self.res.setObjectName("bad")
        self.res.style().unpolish(self.res); self.res.style().polish(self.res)


class ActividadesPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.setObjectName("page")
        l = QVBoxLayout(self)
        l.addWidget(titulo("Actividades económicas, tasas y patentes", "Licencias de funcionamiento con QR verificable, alertas, inspecciones y simulación de patentes. Las tasas y patentes eventuales se cobran en «Otros ingresos»."))
        t = QTabWidget()
        t.addTab(Padron(app), "Establecimientos y licencias")
        t.addTab(Alertas(app), "Alertas y resúmenes")
        t.addTab(Simulador(app), "Simulador de patente")
        t.addTab(Verificar(app), "Verificar licencia")
        l.addWidget(t)
