"""Otros ingresos municipales: Formulario Único de Caja (FUC), control de transacciones y contratos/devengados."""
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

from ..core.paths import reports_dir
from ..reports import formularios as FM
from ..reports.engine import Col, Report, fmt_num
from ..services import otros
from ..services.base import ServiceError, hoy
from .widgets import CrudDialog, DataTable, ExportBar, Field, btn, confirm, guarded, info, open_file, titulo

F = Field


def _subs(db):
    return [(r["codigo"], f"{r['codigo']} – {r['descripcion']}  ({'Bs ' + fmt_num(r['monto']) if r['monto'] else str(r['porcentaje']) + ' %'})")
            for r in db.all("SELECT * FROM subniveles WHERE activo=1 AND tipo<>'AGREGACION' ORDER BY codigo")]


class FucNuevo(QWidget):
    def __init__(self, app, refrescar):
        super().__init__()
        self.app, self.items, self.refrescar = app, [], refrescar
        l = QVBoxLayout(self)
        self.f = CrudDialog("", [F("nombre", "Nombre del contribuyente / beneficiario", required=True), F("documento", "Documento (CI / NIT)"), F("detalle", "Detalle del concepto")], None, None)
        self.f.layout().removeWidget(self.f.form)
        l.addWidget(self.f.form)
        h = QHBoxLayout()
        self.sub = QComboBox()
        self.sub.setMinimumWidth(480)
        self.sub.setEditable(True)
        self.sub.setInsertPolicy(QComboBox.NoInsert)
        self.recargar()
        self.cant = CrudDialog("", [F("cant", "Cantidad", "float", default=1, lo=0.01, hi=1e6), F("base", "Valor base (si el cobro es en %)", "float", hi=1e12)], None, None)
        self.cant.layout().removeWidget(self.cant.form)
        h.addWidget(QLabel("Rubro / subnivel:")); h.addWidget(self.sub, 1); h.addWidget(self.cant.form); h.addWidget(btn("Agregar (F6)", self.agregar, primary=True))
        l.addLayout(h)
        self.t = DataTable([Col("subnivel", "Subnivel"), Col("descripcion", "Descripción", "text", 3), Col("costo", "Costo", "money"), Col("cantidad", "Cantidad", "num"), Col("total", "Total", "money")])
        l.addWidget(self.t, 1)
        bar = QHBoxLayout()
        bar.addWidget(btn("Quitar línea", self.quitar))
        bar.addWidget(btn("Limpiar (F4)", self.limpiar))
        bar.addStretch(1)
        bar.addWidget(btn("Guardar borrador", lambda: self.guardar(False)))
        bar.addWidget(btn("Guardar y recaudar (F10)", lambda: self.guardar(True), primary=True))
        l.addLayout(bar)
        self.tot = QLabel("Total: Bs 0,00")
        self.tot.setObjectName("titulo")
        l.addWidget(self.tot)

    def recargar(self):
        self.sub.clear()
        for c, d in _subs(self.app.db):
            self.sub.addItem(d, c)

    @guarded
    def agregar(self, *_):
        cod = self.sub.currentData()
        if not cod:
            raise ServiceError("Seleccione un subnivel de recaudación.")
        v = self.cant.form.values()
        s = self.app.db.one("SELECT * FROM subniveles WHERE codigo=?", (cod,))
        costo = otros.costo_item(s, v["base"] or None)
        self.items.append(dict(subnivel=cod, cantidad=v["cant"], base=v["base"] or None, descripcion=s["descripcion"], costo=costo, total=costo * v["cant"]))
        self.pintar()

    def pintar(self):
        self.t.set_data(self.items)
        self.tot.setText(f"Total: Bs {fmt_num(sum(i['total'] for i in self.items))}")

    def quitar(self, *_):
        i = self.t.currentRow()
        if 0 <= i < len(self.items):
            self.items.pop(i); self.pintar()

    def limpiar(self, *_):
        self.items = []; self.pintar()
        for n in ("nombre", "documento", "detalle"):
            self.f.form.set(n, "")

    @guarded
    def guardar(self, recaudar):
        self.f.form.validate()
        v = self.f.form.values()
        ctx = self.app.ctx()
        fid = otros.crear_fuc(ctx, v["nombre"], self.items, v["documento"] or "", v["detalle"] or "")
        if recaudar:
            otros.recaudar_fuc(ctx, fid)
        p = reports_dir() / f"fuc_{fid}.pdf"
        FM.generar(ctx, FM.spec_fuc(ctx, fid), p)
        open_file(p)
        self.limpiar()
        self.refrescar()


class Control(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        self.f = CrudDialog("", [F("desde", "Desde", "date"), F("hasta", "Hasta", "date"), F("estado", "Estado", "choice", ["", "BORRADOR", "RECAUDADO", "ANULADO"])], None, None)
        self.f.layout().removeWidget(self.f.form)
        h.addWidget(self.f.form, 1)
        h.addWidget(btn("Mostrar", self.cargar, primary=True))
        l.addLayout(h)
        self.t = DataTable([Col("nro", "FUC"), Col("fecha", "Fecha", "date"), Col("hora", "Hora"), Col("nombre", "Nombre", "text", 2), Col("detalle", "Detalle", "text", 2), Col("estado", "Estado"), Col("total", "Total", "money"), Col("cajero", "Cajero")])
        l.addWidget(self.t, 1)
        bar = QHBoxLayout()
        for tx, s, p, d in (("Consultar / imprimir", self.ver, False, False), ("Recaudar", self.recaudar, True, False), ("Anular…", self.anular, False, True), ("Borrar borrador", self.borrar, False, True)):
            bar.addWidget(btn(tx, s, primary=p, danger=d))
        bar.addStretch(1)
        l.addLayout(bar)
        self.exp = ExportBar(lambda: Report("Control de transacciones FUC", [Col("nro", "FUC"), Col("fecha", "Fecha", "date"), Col("nombre", "Nombre", "text", 2), Col("estado", "Estado"), Col("total", "Total", "money", 1, True)], self.t.rows, code="FUC_CONTROL"), app.ctx)
        l.addWidget(self.exp)
        self.cargar()

    def showEvent(self, e):
        super().showEvent(e)
        self.cargar()

    @guarded
    def cargar(self, *_):
        v = self.f.form.values()
        q, a = "SELECT * FROM fuc WHERE fecha BETWEEN ? AND ?", [v["desde"], v["hasta"]]
        if v["estado"]:
            q += " AND estado=?"; a.append(v["estado"])
        self.t.set_data(self.app.db.all(q + " ORDER BY id DESC", a))

    def _sel(self):
        r = self.t.current_row()
        if not r:
            raise ServiceError("Seleccione un formulario.")
        return r

    @guarded
    def ver(self, *_):
        r = self._sel()
        p = reports_dir() / f"fuc_{r['id']}.pdf"
        FM.generar(self.app.ctx(), FM.spec_fuc(self.app.ctx(), r["id"]), p)
        open_file(p)

    @guarded
    def recaudar(self, *_):
        r = self._sel()
        otros.recaudar_fuc(self.app.ctx(), r["id"])
        self.cargar()

    @guarded
    def anular(self, *_):
        r = self._sel()
        v = CrudDialog.ask("Anular FUC " + r["nro"], [F("motivo", "Motivo", required=True)], parent=self)
        if v:
            otros.anular_fuc(self.app.ctx(), r["id"], v["motivo"]); self.cargar()

    @guarded
    def borrar(self, *_):
        r = self._sel()
        if confirm(self, "¿Borrar el borrador seleccionado?"):
            otros.borrar_fuc(self.app.ctx(), r["id"]); self.cargar()


class Contratos(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        l = QVBoxLayout(self)
        l.addWidget(titulo("Contratos y alquileres (ingresos devengados)", "Registre contratos de alquiler de mercados, concesiones o rentas fijas. El sistema calcula lo devengado, lo percibido (FUC vinculados) y el saldo."))
        bar = QHBoxLayout()
        bar.addWidget(btn("Nuevo contrato", self.nuevo, primary=True))
        bar.addStretch(1)
        l.addLayout(bar)
        self.t = DataTable([Col("nro", "Contrato"), Col("fecha", "Fecha", "date"), Col("subnivel", "Subnivel"), Col("beneficiario", "Beneficiario", "text", 2), Col("periodos", "Periodos", "int"), Col("devengado", "Devengado", "money"), Col("percibido", "Percibido", "money"), Col("saldo", "Saldo", "money")])
        l.addWidget(self.t, 1)
        self.cargar()

    def showEvent(self, e):
        super().showEvent(e)
        self.cargar()

    def cargar(self):
        self.t.set_data(otros.devengados(self.app.db))

    @guarded
    def nuevo(self, *_):
        v = CrudDialog.ask("Nuevo contrato", [F("subnivel", "Subnivel", "choice", _subs(self.app.db), required=True), F("beneficiario", "Beneficiario", required=True), F("documento", "Documento / N° contrato"),
                                              F("monto", "Monto periódico Bs", "float", required=True), F("frecuencia", "Frecuencia", "choice", ["MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL"]), F("inicio", "Inicio", "date"), F("fin", "Fin", "date?")], parent=self, width=620)
        if v:
            otros.crear_contrato(self.app.ctx(), v["subnivel"], v["beneficiario"], v["monto"], v["inicio"], v["fin"], v["documento"] or "", v["frecuencia"])
            self.cargar()


class OtrosPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.setObjectName("page")
        l = QVBoxLayout(self)
        l.addWidget(titulo("Otros ingresos municipales", "Tasas, derechos, patentes eventuales (sentajes, espectáculos), alquileres, multas y otros mediante el Formulario Único de Caja."))
        t = QTabWidget()
        self.ctrl = Control(app)
        t.addTab(FucNuevo(app, self.ctrl.cargar), "Formulario Único de Caja (FUC)")
        t.addTab(self.ctrl, "Control de transacciones")
        t.addTab(Contratos(app), "Contratos y devengados")
        l.addWidget(t)
