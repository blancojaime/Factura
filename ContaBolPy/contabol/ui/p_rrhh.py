"""Activos fijos, planillas de sueldos, aguinaldo/finiquito y órdenes de producción."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ..sistema import ErrorNegocio
from ..util import fdate, fmt, mes_nombre, r2
from . import tema
from .base import ListaCRUD, Pantalla
from .formularios import Campo, FormDialog
from .widgets import CampoFecha, CampoImporte, Columna, Combo, TablaDatos, aviso, boton, confirmar, error, etiqueta, hbox, info, intentar

MESES = [(i, mes_nombre(i)) for i in range(1, 13)]


# =============================================================== activos fijos
class ActivosPantalla(ListaCRUD):
    titulo = "Activos fijos"
    subtitulo = "Registro de bienes con depreciación lineal según el D.S. 24051. La depreciación se calcula y contabiliza mensualmente."

    def __init__(self, ctx, ventana=None):
        cols = [Columna("codigo", "Código", 90), Columna("nombre", "Descripción", 240, estirar=True), Columna("grupo", "Grupo", 160), Columna("fecha_alta", "Alta", 90, "date"),
                Columna("valor_actual", "Valor", 115, "money"), Columna("dep_acum", "Dep. acumulada", 115, "money"), Columna("neto", "Valor neto", 115, "money"), Columna("pct", "% anual", 70, "num", 1),
                Columna("estado_txt", "Estado", 70)]
        super().__init__(ctx, cols, self.datos, [("Nuevo activo", self.nuevo, "primario"), ("Dar de baja", self.baja, "peligro"), ("Grupos…", self.grupos, "")], True, ventana)
        self.botones["Nuevo activo"].setEnabled(ctx.puede("AF.ACTIVOS") and ctx.abierta)

    def datos(self):
        f = self.ctx.activos.listar()
        for a in f:
            a["neto"] = r2(a["valor_actual"] - a["dep_acum"])
            a["estado_txt"] = "Activo" if a["estado"] == "A" else "Baja"
        return f

    def nuevo(self, _=None):
        ctx = self.ctx
        campos = [Campo("codigo", "Código", "txt", True), Campo("nombre", "Descripción", "txt", True, ancho=2),
                  Campo("grupo_id", "Grupo (define vida útil y %)", "combo", True, opciones=[(g["id"], f"{g['nombre']} ({g['pct']:g}%)") for g in ctx.activos.grupos()]),
                  Campo("fecha_alta", "Fecha de alta", "date", True), Campo("valor_original", "Valor de adquisición (Bs)", "money", True),
                  Campo("dep_acum", "Depreciación acumulada previa (si es antiguo)", "money"), Campo("ubicacion", "Ubicación"), Campo("responsable", "Responsable"), Campo("serie", "Serie / placa"),
                  Campo("contra_cuenta_id", "Contrapartida del alta (genera comprobante)", "combo", opciones=[(c["id"], f"{c['codigo']} {c['nombre']}") for c in ctx.cuentas.listar(solo_movimiento=True) if c["tipo"] in ("A", "P", "T")], vacio="(no generar comprobante)", ancho=2)]
        FormDialog("Nuevo activo fijo", campos, {"fecha_alta": min(max(date.today(), ctx.inicio), ctx.fin)}, ctx.activos.guardar, parent=self.ventana or self).exec()

    def baja(self, f):
        if not f:
            return
        campos = [Campo("fecha", "Fecha de baja", "date", True), Campo("venta", "Importe de venta (0 si es baja sin venta)", "money"),
                  Campo("motivo", "Motivo", ancho=2)]
        FormDialog(f"Baja de {f['codigo']}", campos, {"fecha": min(max(date.today(), self.ctx.inicio), self.ctx.fin)},
                   lambda v: self.ctx.activos.baja(f["id"], v["fecha"], v["venta"], None, v["motivo"]), parent=self.ventana or self).exec()

    def grupos(self, _=None):
        info(self, "Grupos de activos (D.S. 24051):\n\n" + "\n".join(f"• {g['nombre']}: {g['vida_anios']:g} años, {g['pct']:g}% anual" for g in self.ctx.activos.grupos()))


class DepreciacionPantalla(Pantalla):
    titulo = "Depreciación y actualización"
    subtitulo = "Calcule la depreciación mensual con vista previa y regístrela en un solo comprobante. La actualización por UFV es opcional (efectos tributarios)."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        top = QHBoxLayout()
        self.mes = Combo(MESES)
        self.mes.set_valor(min(max(date.today().month if date.today().year == ctx.gestion["anio"] else 12, 1), 12))
        self.b_prev = boton("Vista previa")
        self.b_reg = boton("Registrar depreciación", "primario")
        self.b_ufv = boton("Actualizar por UFV…")
        top.addWidget(etiqueta("Mes"))
        top.addWidget(self.mes)
        top.addStretch(1)
        for b in (self.b_prev, self.b_ufv, self.b_reg):
            top.addWidget(b)
        self.cuerpo.addLayout(top)
        self.tabla = TablaDatos([Columna("codigo", "Código", 90), Columna("nombre", "Activo", 240, estirar=True), Columna("grupo", "Grupo", 160), Columna("valor_actual", "Valor", 120, "money"),
                                 Columna("dep_acum", "Dep. acumulada", 120, "money"), Columna("depreciacion", "Depreciación del mes", 150, "money")])
        self.cuerpo.addWidget(self.tabla, 1)
        self.l = QLabel("")
        self.l.setStyleSheet("font-weight:600;")
        self.cuerpo.addWidget(self.l)
        self.b_prev.clicked.connect(self.refrescar)
        self.mes.currentIndexChanged.connect(lambda *_: self.refrescar())
        self.b_reg.clicked.connect(self.registrar)
        self.b_ufv.clicked.connect(self.ufv)
        self.b_reg.setEnabled(ctx.puede("AF.DEPRECIAR") and ctx.abierta)
        self.refrescar()

    def refrescar(self) -> None:
        ok, f = intentar(self, self.ctx.activos.depreciar, self.ctx.gestion["anio"], self.mes.valor(), False)
        f = f if ok else []
        self.tabla.cargar(f)
        self.l.setText(f"{len(f)} activo(s) por depreciar · Total: Bs {fmt(sum(x['depreciacion'] for x in f))}" if f else "No hay depreciación pendiente en este mes.")

    def registrar(self) -> None:
        if confirmar(self, f"Se contabilizará la depreciación de {mes_nombre(self.mes.valor())}. ¿Continuar?"):
            ok, f = intentar(self, self.ctx.activos.depreciar, self.ctx.gestion["anio"], self.mes.valor(), True)
            if ok:
                info(self, f"Depreciación registrada: {len(f)} activo(s).")
                self.refrescar()

    def ufv(self) -> None:
        ok, f = intentar(self, self.ctx.activos.actualizar_ufv, self.ctx.gestion["anio"], self.mes.valor(), False)
        if not ok:
            return
        if not f:
            info(self, "No hay variación de UFV por actualizar en este mes.")
            return
        tot = sum(x["actualizacion"] for x in f)
        if confirmar(self, f"Actualización de {len(f)} activo(s) por Bs {fmt(tot)} (UFV {f[0]['ufv_ini']:.5f} → {f[0]['ufv_fin']:.5f}).\n¿Registrar el comprobante?"):
            ok, _ = intentar(self, self.ctx.activos.actualizar_ufv, self.ctx.gestion["anio"], self.mes.valor(), True)
            if ok:
                info(self, "Actualización registrada.")


# ================================================================== empleados
class EmpleadosPantalla(ListaCRUD):
    titulo = "Empleados"
    subtitulo = "Datos laborales y de seguridad social. El bono de antigüedad se calcula automáticamente."

    def __init__(self, ctx, ventana=None):
        cols = [Columna("codigo", "Código", 80), Columna("nombre", "Nombre", 240, estirar=True), Columna("ci", "CI", 100), Columna("cargo", "Cargo", 160), Columna("fecha_ingreso", "Ingreso", 90, "date"),
                Columna("haber_basico", "Haber básico", 110, "money"), Columna("bono", "Bono antigüedad", 120, "money"), Columna("afp", "AFP", 90), Columna("activo", "Activo", 60, "bool")]
        super().__init__(ctx, cols, self.datos, [("Nuevo empleado", self.editar, "primario"), ("Modificar", self.editar, ""), ("Finiquito…", self.finiquito, "")], True, ventana, doble_clic=self.editar)

    def datos(self):
        f = self.ctx.rrhh.empleados(False)
        for e in f:
            e["bono"] = self.ctx.rrhh.bono_antiguedad(e["fecha_ingreso"], self.ctx.fin)
        return f

    def editar(self, f=None):
        nuevo = not f or "id" not in f
        v = dict(f) if not nuevo else {"fecha_ingreso": date.today(), "activo": 1, "aporta_afp": 1, "afp": "GESTORA"}
        campos = [Campo("codigo", "Código (automático)"), Campo("ci", "Cédula de identidad", "txt", True), Campo("nombre", "Nombre completo", "txt", True, ancho=2), Campo("nua", "NUA / CUA"),
                  Campo("cargo", "Cargo"), Campo("fecha_ingreso", "Fecha de ingreso", "date", True), Campo("fecha_retiro", "Fecha de retiro (si corresponde)", "txt"),
                  Campo("haber_basico", "Haber básico mensual (Bs)", "money", True), Campo("bono_fijo", "Otros bonos fijos mensuales", "money"),
                  Campo("aporta_afp", "Aporta a la Gestora Pública (AFP)", "check"), Campo("mayor_65", "Mayor de 65 años", "check"), Campo("jubilado", "Jubilado", "check"), Campo("activo", "Activo", "check"),
                  Campo("banco", "Banco"), Campo("cuenta_banco", "Nº de cuenta")]

        def guardar(x):
            x["id"] = None if nuevo else f["id"]
            x["fecha_retiro"] = x["fecha_retiro"] or None
            self.ctx.rrhh.guardar_empleado(x)
        FormDialog("Empleado", campos, v, guardar, parent=self.ventana or self).exec()

    def finiquito(self, f):
        if f and self.ventana:
            self.ventana.informe("finiquito", {"empleado": f["id"], "fecha_retiro": self.ctx.fin, "causal": "RETIRO_VOLUNTARIO", "vacaciones": 0})


# ================================================================== planilla
class FilaPlanillaDialog(QDialog):
    def __init__(self, ctx, pid: int, d: dict, parent=None):
        super().__init__(parent)
        self.ctx, self.pid, self.d = ctx, pid, d
        self.setWindowTitle(f"Variables del mes - {d['nombre']}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        h = QLabel(d["nombre"])
        h.setObjectName("h1")
        lay.addWidget(h)
        g = QGridLayout()
        self.dias = CampoImporte(d["dias"], 0)
        self.he = CampoImporte(d["horas_extra"], 1)
        self.hn = CampoImporte(0, 1)
        self.dom = CampoImporte(0, 0)
        self.ob = CampoImporte(d["otros_bonos"])
        self.od = CampoImporte(d["otros_desc"])
        self.rf = CampoImporte(0.0)
        for i, (et, w) in enumerate([("Días trabajados", self.dias), ("Horas extra", self.he), ("Horas nocturnas", self.hn), ("Domingos/feriados trabajados", self.dom),
                                     ("Otros bonos (Bs)", self.ob), ("Otros descuentos (Bs)", self.od), ("Facturas Form. 110 presentadas (Bs)", self.rf)]):
            g.addWidget(etiqueta(et), (i // 2) * 2, i % 2)
            g.addWidget(w, (i // 2) * 2 + 1, i % 2)
        lay.addLayout(g)
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{tema.ROJO};")
        lay.addWidget(self.err)
        ok, ca = boton("Recalcular", "primario", 110), boton("Cancelar", "", 100)
        lay.addLayout(hbox(None, ca, ok))
        ok.clicked.connect(self.guardar)
        ca.clicked.connect(self.reject)

    def guardar(self) -> None:
        try:
            self.ctx.rrhh.recalcular_fila(self.pid, self.d["empleado_id"], {"dias": int(self.dias.valor()), "horas_extra": self.he.valor(), "horas_nocturnas": self.hn.valor(),
                                                                          "domingos": self.dom.valor(), "otros_bonos": self.ob.valor(), "otros_desc": self.od.valor(), "rc_facturas": self.rf.valor()})
        except Exception as ex:  # noqa: BLE001
            self.err.setText(str(ex))
            return
        self.accept()


class PlanillaPantalla(Pantalla):
    titulo = "Planilla de sueldos"
    subtitulo = "Generación mensual con aportes AFP, CNS, Pro-Vivienda, ANS, RC-IVA y bono de antigüedad según la normativa vigente."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        top = QHBoxLayout()
        self.mes = Combo(MESES)
        self.mes.set_valor(min(max(date.today().month if date.today().year == ctx.gestion["anio"] else 12, 1), 12))
        self.est = QLabel("")
        self.est.setStyleSheet("font-weight:600;")
        self.b_gen = boton("Generar / recalcular", "primario")
        self.b_edit = boton("Variables del empleado…")
        self.b_cerrar = boton("Cerrar y contabilizar", "exito")
        self.b_pagar = boton("Registrar pago")
        self.b_rep = boton("Informes…")
        top.addWidget(etiqueta("Mes"))
        top.addWidget(self.mes)
        top.addWidget(self.est)
        top.addStretch(1)
        for b in (self.b_gen, self.b_edit, self.b_cerrar, self.b_pagar, self.b_rep):
            top.addWidget(b)
        self.cuerpo.addLayout(top)
        self.tabla = TablaDatos([Columna("nombre", "Empleado", 220, estirar=True), Columna("dias", "Días", 50, "int"), Columna("haber_basico", "Haber básico", 105, "money"), Columna("bono_antig", "Bono antig.", 95, "money"),
                                 Columna("extras", "Extras y rec.", 95, "money"), Columna("total_ganado", "Total ganado", 110, "money"), Columna("afp", "AFP laboral", 100, "money"), Columna("ans", "ANS", 80, "money"),
                                 Columna("rciva", "RC-IVA", 85, "money"), Columna("anticipos", "Anticipos", 90, "money"), Columna("liquido", "Líquido pagable", 120, "money")])
        self.cuerpo.addWidget(self.tabla, 1)
        self.l = QLabel("")
        self.l.setObjectName("sub")
        self.cuerpo.addWidget(self.l)
        self.mes.currentIndexChanged.connect(lambda *_: self.refrescar())
        self.b_gen.clicked.connect(self.generar)
        self.b_edit.clicked.connect(self.variables)
        self.b_cerrar.clicked.connect(self.cerrar)
        self.b_pagar.clicked.connect(self.pagar)
        self.b_rep.clicked.connect(lambda: self.ventana.informe("planilla_sueldos", {"mes": self.mes.valor()}, pedir=False))
        self.tabla.doble_clic.connect(lambda *_: self.variables())
        self.refrescar()

    def _pl(self):
        return self.ctx.rrhh.planilla(self.ctx.gestion["anio"], self.mes.valor())

    def refrescar(self) -> None:
        pl = self._pl()
        self.tabla.cargar([])
        for b in (self.b_edit, self.b_cerrar, self.b_pagar, self.b_rep):
            b.setEnabled(False)
        editable = self.ctx.puede("RH.PLANILLA") and self.ctx.abierta
        self.b_gen.setEnabled(editable)
        if not pl:
            self.est.setText("   (sin generar)")
            self.l.setText("Pulse «Generar» para calcular la planilla del mes con los empleados vigentes.")
            return
        det = self.ctx.rrhh.detalle(pl["id"])
        for d in det:
            d["afp"] = r2(d["afp_vejez"] + d["afp_riesgo"] + d["afp_comision"] + d["afp_solidario"])
            d["extras"] = r2(d["monto_extra"] + d["recargo_nocturno"] + d["dominical"])
        self.tabla.cargar(det)
        t = self.ctx.rrhh.totales(pl["id"])
        est = {"B": "BORRADOR", "C": "CERRADA", "P": "PAGADA"}[pl["estado"]]
        self.est.setText(f"   Estado: {est}   ·   SMN Bs {fmt(pl['smn'])}")
        self.b_edit.setEnabled(pl["estado"] == "B" and editable)
        self.b_gen.setEnabled(pl["estado"] == "B" and editable)
        self.b_cerrar.setEnabled(pl["estado"] == "B" and editable)
        self.b_pagar.setEnabled(pl["estado"] == "C" and editable)
        self.b_rep.setEnabled(True)
        self.l.setText(f"Total ganado Bs {fmt(t['total_ganado'])}  ·  Descuentos Bs {fmt(t['total_desc'])}  ·  Líquido Bs {fmt(t['liquido'])}  ·  Aportes patronales Bs "
                       f"{fmt(t['pat_cns'] + t['pat_riesgo'] + t['pat_vivienda'] + t['pat_solidario'] + t['pat_infocal'])}")

    def generar(self) -> None:
        ok, _ = intentar(self, self.ctx.rrhh.generar, self.ctx.gestion["anio"], self.mes.valor())
        if ok:
            self.refrescar()

    def variables(self) -> None:
        pl, f = self._pl(), self.tabla.fila_actual()
        if pl and f and pl["estado"] == "B":
            if FilaPlanillaDialog(self.ctx, pl["id"], f, self.ventana or self).exec():
                self.refrescar()

    def cerrar(self) -> None:
        pl = self._pl()
        if pl and confirmar(self, "Se cerrará la planilla y se generará el comprobante contable. ¿Continuar?"):
            ok, _ = intentar(self, self.ctx.rrhh.cerrar, pl["id"])
            if ok:
                self.refrescar()

    def pagar(self) -> None:
        pl = self._pl()
        if pl:
            ok, _ = intentar(self, self.ctx.rrhh.pagar, pl["id"], date(self.ctx.gestion["anio"], self.mes.valor(), 28))
            if ok:
                info(self, "Pago registrado.")
                self.refrescar()


class AnticiposPantalla(ListaCRUD):
    titulo = "Anticipos de sueldo"
    subtitulo = "Adelantos al personal que se descuentan automáticamente en la planilla."

    def __init__(self, ctx, ventana=None):
        cols = [Columna("fecha", "Fecha", 90, "date"), Columna("nombre", "Empleado", 260, estirar=True), Columna("monto", "Monto", 110, "money"), Columna("descuento_mes", "Descuento mensual", 140, "money"),
                Columna("saldo", "Saldo", 110, "money"), Columna("glosa", "Detalle", 200)]
        super().__init__(ctx, cols, lambda: ctx.db.query("SELECT a.*, e.nombre FROM anticipo a JOIN empleado e ON e.id=a.empleado_id ORDER BY a.fecha DESC"),
                         [("Nuevo anticipo", self.nuevo, "primario")], True, ventana)
        self.botones["Nuevo anticipo"].setEnabled(ctx.puede("RH.PLANILLA") and ctx.abierta)

    def nuevo(self, _=None):
        campos = [Campo("empleado_id", "Empleado", "combo", True, opciones=[(e["id"], e["nombre"]) for e in self.ctx.rrhh.empleados()]), Campo("fecha", "Fecha", "date", True),
                  Campo("monto", "Monto (Bs)", "money", True), Campo("descuento_mes", "Descuento mensual (Bs)", "money"), Campo("glosa", "Detalle", ancho=2)]
        FormDialog("Anticipo de sueldo", campos, {"fecha": min(max(date.today(), self.ctx.inicio), self.ctx.fin)},
                   lambda v: self.ctx.rrhh.anticipo(v["empleado_id"], v["fecha"], v["monto"], v["descuento_mes"], v["glosa"]), parent=self.ventana or self).exec()


class BeneficiosPantalla(Pantalla):
    titulo = "Aguinaldo y finiquitos"
    subtitulo = "Aguinaldo de Navidad por empleado y cálculo referencial de beneficios sociales al retiro."

    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, ventana)
        top = QHBoxLayout()
        b1 = boton("Informe de aguinaldo", "primario")
        top.addWidget(b1)
        top.addStretch(1)
        self.cuerpo.addLayout(top)
        self.tabla = TablaDatos([Columna("codigo", "Código", 80), Columna("nombre", "Empleado", 240, estirar=True), Columna("ingreso", "Ingreso", 90, "date"), Columna("dias", "Días", 60, "int"),
                                 Columna("promedio", "Promedio ganado", 130, "money"), Columna("aguinaldo", "Aguinaldo", 120, "money"), Columna("segundo_aguinaldo", "2º aguinaldo", 120, "money"), Columna("total", "Total", 120, "money")])
        self.cuerpo.addWidget(self.tabla, 1)
        b1.clicked.connect(lambda: self.ventana.informe("aguinaldo", pedir=False))
        self.refrescar()

    def refrescar(self) -> None:
        self.tabla.cargar(self.ctx.rrhh.aguinaldo(self.ctx.gestion["anio"]))


# ================================================================ producción
class OrdenDialog(QDialog):
    def __init__(self, ctx, oid: int, parent=None):
        super().__init__(parent)
        self.ctx, self.oid = ctx, oid
        self.vent = parent
        self.resize(900, 620)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 16, 20, 14)
        self.h = QLabel("")
        self.h.setObjectName("h1")
        self.lay.addWidget(self.h)
        self.res = QLabel("")
        self.lay.addWidget(self.res)
        self.tabs = QTabWidget()
        self.t_mp = TablaDatos([Columna("fecha", "Fecha", 90, "date"), Columna("nombre", "Materia prima", 260, estirar=True), Columna("cantidad", "Cantidad", 100, "num"), Columna("costo_unit", "Costo unit.", 110, "num", 4), Columna("costo_total", "Importe", 120, "money")])
        self.t_mod = TablaDatos([Columna("descripcion", "Descripción", 260, estirar=True), Columna("horas", "Horas", 90, "num"), Columna("tarifa", "Tarifa", 100, "money"), Columna("monto", "Importe", 120, "money")])
        self.t_cif = TablaDatos([Columna("concepto", "Concepto", 300, estirar=True), Columna("monto", "Importe", 140, "money")])
        for t, n in ((self.t_mp, "Materia prima"), (self.t_mod, "Mano de obra"), (self.t_cif, "Costos indirectos")):
            self.tabs.addTab(t, n)
        self.lay.addWidget(self.tabs, 1)
        self.b_mp, self.b_mod, self.b_cif, self.b_cerrar, self.b_hoja, self.b_x = (boton("+ Consumo de materia prima"), boton("+ Mano de obra"), boton("+ Costo indirecto"), boton("Cerrar orden", "exito"),
                                                                                    boton("Hoja de costos"), boton("Cerrar ventana"))
        self.lay.addLayout(hbox(self.b_mp, self.b_mod, self.b_cif, None, self.b_hoja, self.b_cerrar, self.b_x))
        self.b_mp.clicked.connect(self.mp)
        self.b_mod.clicked.connect(self.mod)
        self.b_cif.clicked.connect(self.cif)
        self.b_cerrar.clicked.connect(self.cerrar)
        self.b_x.clicked.connect(self.accept)
        self.b_hoja.clicked.connect(lambda: self.vent.informe("hoja_costos", {"orden": self.oid}, pedir=False) if self.vent else None)
        self.cargar()

    def cargar(self) -> None:
        o = self.ctx.produccion.obtener(self.oid)
        self.o = o
        self.h.setText(f"Orden de producción Nº {o['numero']} - {o['item_codigo']} {o['item_nombre']} ({'CERRADA' if o['estado'] == 'C' else 'ABIERTA'})")
        self.res.setText(f"Planificado: {o['cant_plan']:g}   ·   Materia prima: <b>{fmt(o['costo_mp'])}</b>   ·   Mano de obra: <b>{fmt(o['costo_mod'])}</b>   ·   CIF: <b>{fmt(o['costo_cif'])}</b>   ·   "
                         f"Costo total: <b>{fmt(o['costo_total'])}</b>" + (f"   ·   Unitario: <b>{fmt(o['costo_unit'])}</b>" if o["cant_prod"] else ""))
        self.t_mp.cargar(o["mp"])
        self.t_mod.cargar(o["mod"])
        self.t_cif.cargar(o["cif"])
        ab = o["estado"] == "A" and self.ctx.puede("COS.PRODUCCION")
        for b in (self.b_mp, self.b_mod, self.b_cif, self.b_cerrar):
            b.setEnabled(ab)

    def mp(self) -> None:
        mp = [(i["id"], f"{i['codigo']} {i['nombre']}  (stock {i['stock']:g})") for i in self.ctx.inventario.items() if not i["es_servicio"]]
        campos = [Campo("fecha", "Fecha", "date", True), Campo("item_id", "Materia prima", "combo", True, opciones=mp), Campo("cantidad", "Cantidad", "num", True)]
        if FormDialog("Consumo de materia prima", campos, {"fecha": min(max(date.today(), self.ctx.inicio), self.ctx.fin)},
                      lambda v: self.ctx.produccion.consumir_mp(self.oid, v["fecha"], [{"item_id": v["item_id"], "cantidad": v["cantidad"]}]), parent=self).exec():
            self.cargar()

    def mod(self) -> None:
        campos = [Campo("empleado_id", "Empleado (opcional)", "combo", opciones=[(e["id"], e["nombre"]) for e in self.ctx.rrhh.empleados()], vacio="(ninguno)"), Campo("descripcion", "Descripción", ancho=2),
                  Campo("horas", "Horas", "num", True), Campo("tarifa", "Tarifa por hora (0 = según sueldo)", "money")]
        if FormDialog("Mano de obra directa", campos, None, lambda v: self.ctx.produccion.agregar_mod(self.oid, v["empleado_id"], v["horas"], v["tarifa"] or None, v["descripcion"]), parent=self).exec():
            self.cargar()

    def cif(self) -> None:
        campos = [Campo("concepto", "Concepto", "txt", True, ancho=2), Campo("monto", "Importe (Bs)", "money", True)]
        if FormDialog("Costo indirecto de fabricación", campos, None, lambda v: self.ctx.produccion.agregar_cif(self.oid, v["concepto"], v["monto"]), parent=self).exec():
            self.cargar()

    def cerrar(self) -> None:
        campos = [Campo("fecha", "Fecha de cierre", "date", True), Campo("cantidad", "Cantidad producida", "num", True)]
        if FormDialog("Cerrar orden", campos, {"fecha": min(max(date.today(), self.ctx.inicio), self.ctx.fin), "cantidad": self.o["cant_plan"]},
                      lambda v: self.ctx.produccion.cerrar(self.oid, v["fecha"], v["cantidad"]), "El producto terminado ingresa al inventario al costo total de la orden.", self).exec():
            self.cargar()


class ProduccionPantalla(ListaCRUD):
    titulo = "Órdenes de producción"
    subtitulo = "Control de costos por orden: materia prima, mano de obra y costos indirectos. Al cerrar, el producto terminado ingresa al inventario."

    def __init__(self, ctx, ventana=None):
        cols = [Columna("numero", "Nº", 60, "int"), Columna("fecha", "Fecha", 90, "date"), Columna("item_nombre", "Producto", 240, estirar=True), Columna("cant_plan", "Planificado", 100, "num"),
                Columna("cant_prod", "Producido", 100, "num"), Columna("costo_total", "Costo total", 120, "money"), Columna("estado_txt", "Estado", 80)]
        super().__init__(ctx, cols, self.datos, [("Nueva orden", self.nueva, "primario"), ("Abrir orden", self.abrir, "")], True, ventana, doble_clic=self.abrir)
        self.botones["Nueva orden"].setEnabled(ctx.puede("COS.PRODUCCION") and ctx.abierta)

    def datos(self):
        f = self.ctx.produccion.listar()
        for x in f:
            x["estado_txt"] = "Cerrada" if x["estado"] == "C" else "Abierta"
        return f

    def nueva(self, _=None):
        alms = [(a["id"], a["nombre"]) for a in self.ctx.inventario.catalogo("almacen")]
        campos = [Campo("fecha", "Fecha", "date", True), Campo("item_id", "Producto a fabricar", "combo", True, opciones=[(i["id"], f"{i['codigo']} {i['nombre']}") for i in self.ctx.inventario.items() if not i["es_servicio"]], ancho=2),
                  Campo("cantidad", "Cantidad planificada", "num", True), Campo("alm_mp", "Almacén de materia prima", "combo", opciones=alms), Campo("alm_pt", "Almacén de producto terminado", "combo", opciones=alms),
                  Campo("glosa", "Observaciones", ancho=2)]
        res = {}

        def guardar(v):
            res["id"] = self.ctx.produccion.abrir(v["fecha"], v["item_id"], v["cantidad"], v["alm_mp"], v["alm_pt"], v["glosa"])
        if FormDialog("Nueva orden de producción", campos, {"fecha": min(max(date.today(), self.ctx.inicio), self.ctx.fin)}, guardar, parent=self.ventana or self).exec():
            self.refrescar()
            OrdenDialog(self.ctx, res["id"], self.ventana or self).exec()
            self.refrescar()

    def abrir(self, f):
        if f:
            OrdenDialog(self.ctx, f["id"], self.ventana or self).exec()
