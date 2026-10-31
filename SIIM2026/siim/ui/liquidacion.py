"""Liquidación: individual (IPBI, IPVA, PAF, Publicidad), masiva, IMT y planes de pago."""
from datetime import date

from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QTabWidget, QVBoxLayout, QWidget)

from ..core.paths import reports_dir
from ..reports import engine
from ..reports import formularios as FM
from ..reports.engine import Col, Report, fmt_num
from ..services import liquidacion as L
from ..services import padron
from ..services import recaudacion as R
from ..services.base import ServiceError, hoy
from .padron import ContribuyenteDialog, elegir_pmc
from .widgets import CrudDialog, DataTable, ExportBar, Field, btn, card, confirm, guarded, info, open_file, titulo

F = Field
OBJ_COLS = {
    "IPBI": [Col("id", "ID", "int"), Col("tipo", "Tipo"), Col("calle", "Calle", "text", 2), Col("numero", "N°"), Col("zona", "Zona"), Col("superficie", "Terreno m²", "money"), Col("sup_construida", "Constr. m²", "money")],
    "IPVA": [Col("id", "ID", "int"), Col("placa", "Placa"), Col("tipo", "Tipo"), Col("marca", "Marca"), Col("modelo", "Modelo"), Col("anio_fab", "Año"), Col("cilindrada", "cc", "int")],
    "PAF": [Col("id", "ID", "int"), Col("nombre_comercial", "Establecimiento", "text", 2), Col("act", "Act"), Col("cat", "Cat"), Col("zona", "Zona"), Col("superficie", "m²", "money"), Col("fecha_inicio", "Inicio", "date")],
    "PUB": [Col("id", "ID", "int"), Col("tipo", "Tipo"), Col("descripcion", "Descripción", "text", 2), Col("ubicacion", "Ubicación")],
}


def gestiones(db):
    a, b = int(db.param("gestion_desde")), int(db.param("gestion_hasta"))
    return list(range(b, a - 1, -1))


class PmcBox(QWidget):
    """Campo PMC con búsqueda multiacceso (F6) y nombre."""

    def __init__(self, app, on_change=None, solo_con=None):
        super().__init__()
        self.app, self.cb, self.solo_con = app, on_change, solo_con
        l = QHBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        self.e = QLineEdit()
        self.e.setPlaceholderText("PMC")
        self.e.setMaximumWidth(130)
        self.e.editingFinished.connect(self.changed)
        l.addWidget(self.e)
        l.addWidget(btn("Buscar (F6)", self.buscar))
        self.n = QLabel("—")
        l.addWidget(self.n, 1)

    @property
    def pmc(self):
        t = self.e.text().strip()
        return int(t) if t.isdigit() else None

    def buscar(self, *_):
        p = elegir_pmc(self.app, self, self.solo_con)
        if p:
            self.e.setText(str(p))
            self.changed()

    def set(self, pmc):
        self.e.setText(str(pmc) if pmc else "")
        self.changed()

    def changed(self):
        if self.pmc:
            c = self.app.db.one("SELECT * FROM contribuyentes WHERE pmc=?", (self.pmc,))
            self.n.setText(f"{padron.nombre_completo(c)}  [{c['estado']}]" if c else "No existe")
        else:
            self.n.setText("—")
        if self.cb:
            self.cb()


class Individual(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.pre = app, None
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        self.rubro = QComboBox()
        for k, v in (("IPBI", "IPBI – Inmuebles"), ("IPVA", "IPVA – Vehículos"), ("PAF", "PAF – Patente de funcionamiento"), ("PUB", "Publicidad y propaganda")):
            self.rubro.addItem(v, k)
        self.gest = QComboBox()
        self.tipo = QComboBox(); self.tipo.addItem("Original", "ORIGINAL"); self.tipo.addItem("Rectificatoria", "RECTIFICATORIA")
        self.forma = QComboBox(); self.forma.addItem("Al contado", "CONTADO"); self.forma.addItem("En dos cuotas", "CUOTAS")
        for t, w in (("Rubro", self.rubro), ("Gestión", self.gest), ("Liquidación", self.tipo), ("Forma de pago", self.forma)):
            h.addWidget(QLabel(t)); h.addWidget(w)
        h.addStretch(1)
        l.addLayout(h)
        self.pmcbox = PmcBox(app, self.cargar_objetos)
        l.addWidget(self.pmcbox)
        self.objs = DataTable(OBJ_COLS["IPBI"])
        self.objs.setMaximumHeight(170)
        l.addWidget(self.objs)
        bar = QHBoxLayout()
        bar.addWidget(btn("Calcular", self.calcular, primary=True))
        self.b_bol = btn("Boleta resumen (PDF)", self.boleta)
        self.b_emit = btn("Emitir liquidación y formulario (PDF)", self.emitir, primary=True)
        bar.addWidget(self.b_bol); bar.addWidget(self.b_emit); bar.addStretch(1)
        l.addLayout(bar)
        self.det = DataTable([Col("c", "Concepto", "text", 3), Col("v", "Valor", "text", 1.2)])
        l.addWidget(self.det, 1)
        self.res = QLabel("")
        self.res.setObjectName("titulo")
        l.addWidget(self.res)
        self.rubro.currentIndexChanged.connect(self.cambio_rubro)
        self.gest.addItems([str(g) for g in gestiones(app.db)])
        self._btns(False)

    def _btns(self, v):
        self.b_bol.setEnabled(v)
        self.b_emit.setEnabled(v)

    def cambio_rubro(self, *_):
        self.objs.set_cols(OBJ_COLS[self.rubro.currentData()])
        self.cargar_objetos()

    def cargar_objetos(self):
        r = self.rubro.currentData()
        self.objs.set_cols(OBJ_COLS[r])
        self.objs.set_data(padron.objetos(self.app.db, L.TABLA[r], self.pmcbox.pmc) if self.pmcbox.pmc else [])
        self.det.set_data([]); self.res.setText(""); self._btns(False); self.pre = None

    @guarded
    def calcular(self, *_):
        o = self.objs.current_row()
        if not o:
            raise ServiceError("Seleccione el bien o actividad a liquidar.")
        self.pre = L.preliquidar(self.app.ctx(), self.rubro.currentData(), o["id"], int(self.gest.currentText()), self.forma.currentData(), self.tipo.currentData())
        rows = [dict(c=a, v=b) for a, b in FM.lineas_detalle(self.pre["rubro"], self.pre["detalle"])]
        rows += [dict(c="Impuesto determinado", v=fmt_num(self.pre["impuesto"]))]
        if self.pre["credito"]:
            rows.append(dict(c="(–) Pagos anteriores (rectificatoria)", v=fmt_num(self.pre["credito"])))
        self.det.set_data(rows)
        self.res.setText(f"IMPORTE NETO: Bs {fmt_num(self.pre['neto'])}   (vence {self.pre['fecha_venc'][8:]}/{self.pre['fecha_venc'][5:7]}/{self.pre['fecha_venc'][:4]} con 10 % de descuento)")
        self._btns(True)

    @guarded
    def boleta(self, *_):
        p = reports_dir() / "boleta_resumen.pdf"
        FM.generar(self.app.ctx(), FM.spec_liquidacion(self.app.ctx(), 0, self.pre), p)
        open_file(p)

    @guarded
    def emitir(self, *_):
        if not self.pre:
            return
        lid = L.guardar_liquidacion(self.app.ctx(), self.pre)
        nro = self.app.db.scalar("SELECT nro FROM liquidaciones WHERE id=?", (lid,))
        p = reports_dir() / f"{nro}.pdf"
        FM.generar(self.app.ctx(), FM.spec_liquidacion(self.app.ctx(), lid), p)
        open_file(p)
        info(self, f"Liquidación {nro} emitida. Código de pago: {self.app.db.scalar('SELECT codigo_pago FROM liquidaciones WHERE id=?', (lid,))}")
        self.pre = None
        self._btns(False)


class Masiva(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.rows = app, []
        l = QVBoxLayout(self)
        l.addWidget(titulo("Liquidación masiva de contribuyentes en mora", "Determina la deuda de todos los bienes/actividades sin liquidación vigente de una gestión vencida. Puede emitir las liquidaciones y las intimaciones (F-345)."))
        h = QHBoxLayout()
        self.rubro = QComboBox()
        for k in ("IPBI", "IPVA", "PAF", "PUB"):
            self.rubro.addItem(k, k)
        self.gest = QComboBox(); self.gest.addItems([str(g) for g in gestiones(app.db)])
        self.zona = QComboBox(); self.zona.addItem("Todas", None)
        for z in app.db.all("SELECT codigo, descripcion FROM zonas ORDER BY 1"):
            self.zona.addItem(f"{z[0]} – {z[1]}", z[0])
        self.vencidas = QCheckBox("Sólo gestiones vencidas"); self.vencidas.setChecked(True)
        for t, w in (("Rubro", self.rubro), ("Gestión", self.gest), ("Zona", self.zona)):
            h.addWidget(QLabel(t)); h.addWidget(w)
        h.addWidget(self.vencidas); h.addStretch(1)
        l.addLayout(h)
        self.pmcbox = PmcBox(app)
        l.addWidget(self.pmcbox)
        bar = QHBoxLayout()
        bar.addWidget(btn("Previsualizar", lambda: self.run(False), primary=True))
        bar.addWidget(btn("Procesar y emitir liquidaciones", lambda: self.run(True)))
        bar.addWidget(btn("Intimación F-345 al seleccionado", self.intimar))
        bar.addStretch(1)
        l.addLayout(bar)
        self.t = DataTable([Col("pmc", "PMC"), Col("nombre", "Contribuyente", "text", 2.5), Col("descripcion", "Bien / actividad", "text", 3), Col("neto", "Impuesto", "money"), Col("mora", "Días mora", "int"), Col("total_hoy", "Deuda hoy", "money"), Col("liq_id", "Liq.")])
        l.addWidget(self.t, 1)
        self.exp = ExportBar(self.reporte, app.ctx)
        l.addWidget(self.exp)
        self.lbl = QLabel()
        l.addWidget(self.lbl)

    @guarded
    def run(self, guardar):
        if guardar and not confirm(self, "Se emitirán liquidaciones definitivas para todos los registros listados. ¿Continuar?"):
            return
        rows, errs = L.liquidar_masiva(self.app.ctx(), self.rubro.currentData(), int(self.gest.currentText()), self.zona.currentData(), None, self.pmcbox.pmc, guardar, self.vencidas.isChecked())
        self.rows = [dict(r, nombre=self.app.db.scalar("SELECT COALESCE(NULLIF(razon_social,''), trim(IFNULL(paterno,'')||' '||IFNULL(materno,'')||' '||IFNULL(nombre,''))) FROM contribuyentes WHERE pmc=?", (r["pmc"],), "")) for r in rows]
        self.t.set_data(self.rows)
        tot = sum(r["total_hoy"] for r in rows)
        self.lbl.setText(f"{len(rows)} registros · Deuda total a hoy: Bs {fmt_num(tot)} · {len(errs)} observación(es)" + ("".join(f"\n  • PMC {e[0]}: {e[1]}" for e in errs[:6])))

    def reporte(self):
        return Report(f"Liquidación masiva {self.rubro.currentData()} gestión {self.gest.currentText()}", [Col("pmc", "PMC"), Col("nombre", "Contribuyente", "text", 2.5), Col("descripcion", "Bien / actividad", "text", 3), Col("neto", "Impuesto", "money", 1, True),
                      Col("mora", "Días mora", "int"), Col("total_hoy", "Deuda hoy Bs", "money", 1, True)], self.rows, code="LIQ_MASIVA")

    @guarded
    def intimar(self, *_):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un contribuyente de la lista.")
        p = reports_dir() / f"F345_{r['pmc']}.pdf"
        FM.generar(self.app.ctx(), FM.spec_intimacion(self.app.ctx(), r["pmc"]), p)
        open_file(p)


class Imt(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.lid = app, None
        l = QVBoxLayout(self)
        l.addWidget(titulo("Impuesto Municipal a las Transferencias (IMT)", "3 % sobre el mayor valor entre lo pagado y la base imponible del IPBI/IPVA de la última gestión vencida. Pago dentro de 10 días hábiles. El cambio de propietario se aplica al cancelar el impuesto."))
        h = QHBoxLayout()
        self.tipo = QComboBox(); self.tipo.addItem("Inmueble", "INM"); self.tipo.addItem("Vehículo automotor", "VEH")
        h.addWidget(QLabel("Bien transferido")); h.addWidget(self.tipo); h.addStretch(1)
        l.addLayout(h)
        l.addWidget(QLabel("Vendedor (debe tener el bien registrado):"))
        self.vend = PmcBox(app, self.carga)
        l.addWidget(self.vend)
        l.addWidget(QLabel("Comprador (debe estar empadronado):"))
        self.comp = PmcBox(app)
        l.addWidget(self.comp)
        l.addWidget(btn("Registrar nuevo comprador (F-019)…", self.nuevo_comp))
        self.objs = DataTable(OBJ_COLS["IPBI"])
        self.objs.setMaximumHeight(150)
        l.addWidget(self.objs)
        self.f = CrudDialog("", [F("fecha_minuta", "Fecha de la minuta / contrato", "date", required=True), F("monto_bs", "Monto de la transferencia (Bs)", "float", hi=1e12), F("monto_usd", "Monto (US$)", "float", hi=1e12), F("nro_ddrr", "N° registro Derechos Reales / póliza")], None, None)
        self.f.layout().removeWidget(self.f.form)
        l.addWidget(self.f.form)
        bar = QHBoxLayout()
        bar.addWidget(btn("Determinar impuesto y emitir F-502/503", self.liquidar, primary=True))
        bar.addStretch(1)
        l.addLayout(bar)
        self.res = QLabel()
        self.res.setObjectName("titulo")
        l.addWidget(self.res)
        self.tipo.currentIndexChanged.connect(self.carga)

    def carga(self):
        r = "IPBI" if self.tipo.currentData() == "INM" else "IPVA"
        self.objs.set_cols(OBJ_COLS[r])
        self.objs.set_data(padron.objetos(self.app.db, L.TABLA[r], self.vend.pmc) if self.vend.pmc else [])

    @guarded
    def nuevo_comp(self, *_):
        v = CrudDialog.ask("Documentación de respaldo F-019", [F("nro_orden", "N° de orden F-019", required=True), F("fecha", "Fecha", "date")], parent=self)
        if v:
            d = ContribuyenteDialog(self.app, "F-019", None, v["nro_orden"], self)
            d.exec()
            if d.pmc:
                self.comp.set(d.pmc)

    @guarded
    def liquidar(self, *_):
        o = self.objs.current_row()
        if not o or not self.vend.pmc or not self.comp.pmc:
            raise ServiceError("Indique vendedor, comprador y seleccione el bien.")
        self.f.form.validate()
        v = self.f.form.values()
        if v["monto_bs"] <= 0 and v["monto_usd"] > 0:
            usd, _, _ = __import__("siim.services.base", fromlist=["cotizacion"]).cotizacion(self.app.db, v["fecha_minuta"])
            v["monto_bs"] = float(usd) * v["monto_usd"]
        lid, tid = L.liquidar_imt(self.app.ctx(), self.tipo.currentData(), self.vend.pmc, self.comp.pmc, o["id"], v["fecha_minuta"], v["monto_bs"], v["monto_usd"], {"nro_ddrr": v["nro_ddrr"]})
        liq = self.app.db.one("SELECT * FROM liquidaciones WHERE id=?", (lid,))
        self.res.setText(f"IMT: Bs {fmt_num(liq['impuesto'])} – pagar hasta {liq['fecha_venc'][8:]}/{liq['fecha_venc'][5:7]}/{liq['fecha_venc'][:4]}")
        p = reports_dir() / f"{liq['nro']}.pdf"
        FM.generar(self.app.ctx(), FM.spec_liquidacion(self.app.ctx(), lid), p)
        open_file(p)


class Planes(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        l.addWidget(titulo("Plan de pagos (facilidades de pago)", "Seleccione las liquidaciones vencidas a financiar. Se concede por una sola vez (Art. 55 Ley 2492). El plan se calcula sobre la deuda tributaria a la fecha, sin el descuento por pago al contado."))
        self.pmcbox = PmcBox(app, self.cargar)
        l.addWidget(self.pmcbox)
        self.t = DataTable([Col("nro", "Liquidación"), Col("rubro", "Rubro"), Col("gestion", "Gestión"), Col("objeto_desc", "Bien / actividad", "text", 3), Col("neto", "Impuesto", "money"), Col("deuda", "Deuda hoy", "money")])
        self.t.setSelectionMode(QAbstractItemView.MultiSelection)
        l.addWidget(self.t, 1)
        self.f = CrudDialog("", [F("n", "N° de cuotas", "int", lo=1, hi=120, default=12), F("ci", "Cuota inicial Bs (0 = % por defecto)", "float", hi=1e12), F("tasa", "Tasa anual (ej. 0,1082)", "float", decimals=4, default=float(app.db.param("plan_tasa_anual", "0.1082"))),
                                           F("res", "N° de resolución de aprobación")], None, None)
        self.f.layout().removeWidget(self.f.form)
        l.addWidget(self.f.form)
        bar = QHBoxLayout()
        bar.addWidget(btn("Crear plan y emitir cronograma", self.crear, primary=True))
        bar.addStretch(1)
        l.addLayout(bar)

    @guarded
    def cargar(self, *_):
        pmc = self.pmcbox.pmc
        rows = []
        if pmc:
            for liq in self.app.db.all("SELECT * FROM liquidaciones WHERE pmc=? AND estado='PENDIENTE' AND forma_pago='CONTADO' ORDER BY gestion", (pmc,)):
                try:
                    d = R.deuda_plan(self.app.db, liq, hoy())
                except ServiceError:
                    d = liq["neto"]
                rows.append(dict(liq, deuda=d))
        self.t.set_data(rows)

    @guarded
    def crear(self, *_):
        sel = sorted({i.row() for i in self.t.selectedIndexes()})
        if not sel:
            raise ServiceError("Seleccione al menos una liquidación (clic en las filas).")
        v = self.f.form.values()
        pid = R.crear_plan(self.app.ctx(), self.pmcbox.pmc, [self.t.rows[i]["id"] for i in sel], v["n"], v["ci"] or None, v["tasa"], v["res"] or "")
        p = reports_dir() / f"plan_{pid}.pdf"
        FM.generar(self.app.ctx(), FM.spec_plan(self.app.ctx(), pid), p)
        open_file(p)
        self.cargar()


class LiquidacionPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.setObjectName("page")
        l = QVBoxLayout(self)
        l.addWidget(titulo("Liquidación", "Determinación automática de impuestos y patentes, con emisión de formularios F-1980, F-2160, F-501 y F-502/503."))
        t = QTabWidget()
        t.addTab(Individual(app), "Liquidación individual")
        t.addTab(Masiva(app), "Liquidación masiva / evasores")
        t.addTab(Imt(app), "Transferencias (IMT)")
        t.addTab(Planes(app), "Planes de pago")
        l.addWidget(t)
