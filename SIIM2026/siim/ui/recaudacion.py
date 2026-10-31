"""Recaudación: cobro de liquidaciones, recibos, anulación, conciliación bancaria y planes de pago."""
from datetime import date

from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QTabWidget, QVBoxLayout, QWidget

from ..core.paths import reports_dir
from ..reports import engine
from ..reports import formularios as FM
from ..reports.engine import Col, fmt_num
from ..services import liquidacion as L
from ..services import recaudacion as R
from ..services.base import ServiceError, hoy
from .liquidacion import PmcBox
from .mantenimiento import leer_tabla
from .widgets import CrudDialog, DataTable, Field, btn, confirm, guarded, info, open_file, titulo

F = Field


class Cobro(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.liq, self.d = app, None, None
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        self.modo = QComboBox()
        for k, v in (("pmc", "N° PMC"), ("placa", "Placa"), ("codigo", "Código de pago"), ("nro", "N° de liquidación")):
            self.modo.addItem(v, k)
        self.txt = QLineEdit()
        self.txt.setPlaceholderText("Dato a buscar (o use Buscar F6 para el PMC)")
        self.txt.returnPressed.connect(self.buscar)
        h.addWidget(QLabel("Buscar por")); h.addWidget(self.modo); h.addWidget(self.txt, 1)
        h.addWidget(btn("Buscar", self.buscar, primary=True))
        h.addWidget(btn("Buscar contribuyente (F6)", self.f6))
        l.addLayout(h)
        self.t = DataTable([Col("nro", "Liquidación"), Col("rubro", "Rubro"), Col("gestion", "Gest."), Col("objeto_desc", "Bien / actividad", "text", 3), Col("forma_pago", "Forma"), Col("neto", "Impuesto", "money"), Col("estado", "Estado")])
        self.t.seleccion.connect(lambda *_: self.calcular())
        l.addWidget(self.t, 1)
        row = QHBoxLayout()
        self.fecha = CrudDialog("", [F("fecha", "Fecha de pago", "date", required=True), F("cuota", "Cuota", "choice", [("", "Pago total")]), F("modalidad", "Modalidad", "choice", ["CAJA", "BANCO"]), F("entidad", "Entidad financiera")], None, None)
        self.fecha.layout().removeWidget(self.fecha.form)
        row.addWidget(self.fecha.form, 1)
        l.addLayout(row)
        self.fecha.form.w["fecha"].dateChanged.connect(lambda *_: self.calcular())
        self.fecha.form.w["cuota"].currentIndexChanged.connect(lambda *_: self.calcular(False))
        self.det = DataTable([Col("c", "Concepto", "text", 3), Col("v", "Bs", "money")])
        self.det.setMaximumHeight(210)
        l.addWidget(self.det)
        self.tot = QLabel("")
        self.tot.setObjectName("titulo")
        l.addWidget(self.tot)
        bar = QHBoxLayout()
        self.bc = btn("Registrar pago (F10)", self.cobrar, primary=True)
        bar.addWidget(self.bc); bar.addStretch(1)
        l.addLayout(bar)
        self.bc.setEnabled(False)

    def f6(self, *_):
        from .padron import elegir_pmc
        p = elegir_pmc(self.app, self)
        if p:
            self.modo.setCurrentIndex(0)
            self.txt.setText(str(p))
            self.buscar()

    @guarded
    def buscar(self, *_):
        m, t = self.modo.currentData(), self.txt.text().strip()
        db = self.app.db
        base = "SELECT * FROM liquidaciones WHERE estado IN ('PENDIENTE','PARCIAL')"
        if m == "pmc" and t.isdigit():
            rows = db.all(base + " AND pmc=? ORDER BY gestion, rubro", (int(t),))
        elif m == "placa":
            rows = db.all(base + " AND rubro='IPVA' AND objeto_id IN (SELECT id FROM vehiculos WHERE placa=?) ORDER BY gestion", (t.upper(),))
        elif m == "codigo":
            rows = db.all(base + " AND codigo_pago=?", (t,))
        elif m == "nro":
            rows = db.all(base + " AND nro=?", (t,))
        else:
            rows = []
        self.t.set_data(rows)
        self.det.set_data([]); self.tot.setText("")
        if not rows:
            info(self, "No hay liquidaciones pendientes para el criterio indicado.\nSi el contribuyente no tiene liquidación, genérela en el módulo Liquidación.")
        elif len(rows) == 1:
            self.t.selectRow(0)

    @guarded
    def calcular(self, reload_cuotas=True):
        r = self.t.current_row()
        self.bc.setEnabled(False)
        if not r:
            return
        w = self.fecha.form.w["cuota"]
        if reload_cuotas:
            qs = self.app.db.all("SELECT * FROM liq_cuotas WHERE liq_id=? AND estado='PENDIENTE' ORDER BY nro", (r["id"],))
            w.blockSignals(True)
            w.clear()
            if r["forma_pago"] == "CUOTAS":
                for q in qs:
                    w.addItem(f"Cuota {q['nro']} – vence {q['vence']}", q["id"])
            else:
                w.addItem("Pago total", None)
            w.blockSignals(False)
        cid = w.currentData()
        self.liq = self.app.db.one("SELECT * FROM liquidaciones WHERE id=?", (r["id"],))
        self.d = L.deuda_a_fecha(self.app.db, self.liq, self.fecha.form.get("fecha"), cid)
        d = self.d
        rows = [dict(c=f"Impuesto ({d['concepto'] or 'pago total'})", v=d["neto"])]
        for lab, k, s in (("(–) Descuento por pago al contado", "descuento", -1), ("(+) Mantenimiento de valor", "mant_valor", 1), ("(+) Intereses", "interes", 1), ("(+) Multa por incumplimiento de deberes formales", "multa_df", 1), ("(+) Sanción administrativa", "sancion", 1)):
            if d[k]:
                rows.append(dict(c=lab, v=d[k] * s))
        if d["en_mora"]:
            rows.append(dict(c=f"Mora: {d['mora']} días · UFV venc. {d['ufv_fv']} · UFV pago {d['ufv_fp']} · r {d['r'] * 100:.2f} %", v=None))
        self.det.set_data(rows)
        self.tot.setText(f"TOTAL A PAGAR: Bs {fmt_num(d['total'])}" + ("   ⚠ EN MORA" if d["en_mora"] else ""))
        self.bc.setEnabled(self.app.session.can("rec.cobrar"))

    @guarded
    def cobrar(self, *_):
        f = self.fecha.form.values()
        if not confirm(self, f"¿Registrar el pago de Bs {fmt_num(self.d['total'])}?\n\nEsta operación afecta los listados de recaudación."):
            return
        pid = R.cobrar(self.app.ctx(), self.liq["id"], f["fecha"], f["modalidad"], f["entidad"] or "", f["cuota"], self.d["total"])
        p = reports_dir() / f"recibo_{pid}.pdf"
        FM.generar(self.app.ctx(), FM.spec_recibo(self.app.ctx(), pid), p)
        open_file(p)
        self.buscar()


class PagosDia(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        self.f = CrudDialog("", [F("fecha", "Fecha", "date")], None, None)
        self.f.layout().removeWidget(self.f.form)
        h.addWidget(self.f.form)
        h.addWidget(btn("Mostrar", self.cargar, primary=True))
        h.addWidget(btn("Reimprimir recibo", self.recibo))
        h.addWidget(btn("Anular pago…", self.anular, danger=True))
        h.addStretch(1)
        l.addLayout(h)
        self.t = DataTable([Col("nro_recibo", "Recibo"), Col("hora", "Hora"), Col("rubro", "Rubro"), Col("gestion", "Gest."), Col("pmc", "PMC"), Col("modalidad", "Modalidad"), Col("total", "Total Bs", "money"), Col("estado", "Estado")])
        l.addWidget(self.t, 1)
        self.lbl = QLabel()
        self.lbl.setObjectName("titulo")
        l.addWidget(self.lbl)
        self.cargar()

    def showEvent(self, e):
        super().showEvent(e)
        self.cargar()

    @guarded
    def cargar(self, *_):
        rows = self.app.db.all("SELECT * FROM pagos WHERE fecha=? ORDER BY id", (self.f.form.get("fecha"),))
        self.t.set_data(rows)
        self.lbl.setText(f"Total recaudado (vigente): Bs {fmt_num(sum(r['total'] for r in rows if r['estado'] == 'VIGENTE'))}")

    @guarded
    def recibo(self, *_):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un pago.")
        p = reports_dir() / f"recibo_{r['id']}.pdf"
        FM.generar(self.app.ctx(), FM.spec_recibo(self.app.ctx(), r["id"]), p)
        open_file(p)

    @guarded
    def anular(self, *_):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un pago.")
        v = CrudDialog.ask("Anular pago " + r["nro_recibo"], [F("motivo", "Motivo de la anulación", required=True)], parent=self)
        if v:
            R.anular_pago(self.app.ctx(), r["id"], v["motivo"])
            self.cargar()


class Conciliacion(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        l.addWidget(titulo("Conciliación bancaria", "Cargue el archivo (Excel o CSV) de la entidad financiera con las columnas: codigo_pago, monto, fecha. Se registran los pagos cuyo monto coincide con lo calculado por el sistema; el resto queda observado."))
        h = QHBoxLayout()
        self.ent = QLineEdit(); self.ent.setPlaceholderText("Entidad financiera")
        h.addWidget(self.ent, 1)
        h.addWidget(btn("Seleccionar archivo y procesar…", self.procesar, primary=True))
        l.addLayout(h)
        self.t = DataTable([Col("estado", "Resultado"), Col("codigo", "Código de pago"), Col("detalle", "Detalle", "text", 4)])
        l.addWidget(self.t, 1)

    @guarded
    def procesar(self, *_):
        if not self.ent.text().strip():
            raise ServiceError("Indique la entidad financiera.")
        fn, _ = QFileDialog.getOpenFileName(self, "Archivo del banco", "", "Excel/CSV (*.xlsx *.csv)")
        if not fn:
            return
        filas = leer_tabla(fn)
        for r in filas:
            r["monto"] = float(str(r.get("monto", 0)).replace(",", "."))
        ok, obs = R.conciliar_banco(self.app.ctx(), filas, self.ent.text().strip())
        self.t.set_data([dict(estado="REGISTRADO", codigo=c, detalle=f"Pago {p}") for c, p in ok] + [dict(estado="OBSERVADO", codigo=c, detalle=m) for c, m in obs])
        info(self, f"{len(ok)} pagos registrados · {len(obs)} observados.")


class PlanesPago(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        l.addWidget(titulo("Cobro de cuotas de planes de pago"))
        self.pmcbox = PmcBox(app, self.cargar)
        l.addWidget(self.pmcbox)
        self.t = DataTable([Col("plan", "Plan"), Col("nro", "Cuota", "int"), Col("vence", "Vence", "date"), Col("monto", "Monto Bs", "money"), Col("saldo", "Saldo", "money"), Col("estado", "Estado")])
        l.addWidget(self.t, 1)
        bar = QHBoxLayout()
        bar.addWidget(btn("Pagar cuota seleccionada", self.pagar, primary=True))
        bar.addWidget(btn("Imprimir cronograma", self.imprimir))
        bar.addStretch(1)
        l.addLayout(bar)

    @guarded
    def cargar(self, *_):
        pmc = self.pmcbox.pmc
        self.t.set_data(self.app.db.all("SELECT q.*, p.nro AS plan, p.id AS plan_id FROM plan_cuotas q JOIN planes_pago p ON p.id=q.plan_id WHERE p.pmc=? ORDER BY p.id, q.nro", (pmc,)) if pmc else [])

    @guarded
    def pagar(self, *_):
        r = self.t.current_row()
        if not r or r["estado"] != "PENDIENTE":
            raise ServiceError("Seleccione una cuota pendiente.")
        pid = R.pagar_cuota_plan(self.app.ctx(), r["id"])
        p = reports_dir() / f"recibo_{pid}.pdf"
        FM.generar(self.app.ctx(), FM.spec_recibo(self.app.ctx(), pid), p)
        open_file(p)
        self.cargar()

    @guarded
    def imprimir(self, *_):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione una cuota del plan.")
        p = reports_dir() / f"plan_{r['plan_id']}.pdf"
        FM.generar(self.app.ctx(), FM.spec_plan(self.app.ctx(), r["plan_id"]), p)
        open_file(p)


class RecaudacionPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.setObjectName("page")
        l = QVBoxLayout(self)
        l.addWidget(titulo("Recaudación", "Registro de pagos en caja o entidades financieras. El sistema calcula descuentos y accesorios a la fecha de pago."))
        t = QTabWidget()
        t.addTab(Cobro(app), "Registrar pago")
        t.addTab(PagosDia(app), "Pagos del día / anulación")
        t.addTab(Conciliacion(app), "Conciliación bancaria")
        t.addTab(PlanesPago(app), "Cuotas de planes de pago")
        l.addWidget(t)
