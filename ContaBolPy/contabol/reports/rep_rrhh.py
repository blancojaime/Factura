"""Informes laborales: planillas, aportes, RC-IVA, boletas, aguinaldo y finiquitos."""
from __future__ import annotations

from ..sistema import ErrorNegocio
from ..util import fdate, fin_de_mes, mes_nombre, monto_en_letras
from .catalogo import MOD_RH, P_DESDE, P_HASTA, ParamDef, reporte
from .engine import Col, base

PERM = "RH.REPORTES"
MES = lambda: ParamDef("mes", "Mes", "mes", 1)  # noqa: E731


def _plan(ctx, p):
    pl = ctx.rrhh.planilla(ctx.gestion["anio"], int(p["mes"]))
    if not pl:
        raise ErrorNegocio(f"No existe planilla de {mes_nombre(int(p['mes']))}. Genérela primero en Planillas > Planilla de sueldos.")
    return pl, ctx.rrhh.detalle(pl["id"])


@reporte("planilla_sueldos", "Planilla de sueldos y salarios", MOD_RH, PERM, [MES()])
def planilla_sueldos(ctx, p):
    pl, det = _plan(ctx, p)
    rep = base(ctx, "Planilla de Sueldos y Salarios", f"{mes_nombre(pl['mes'])} de {pl['anio']}", f"Salario mínimo nacional vigente: Bs {pl['smn']:,.2f}", horizontal=True)
    rep.firmas = ["Elaborado por", "Gerente Administrativo", "Representante Legal"]
    t = rep.tabla([Col("Nº", .5, "int"), Col("Nombre", 3), Col("CI", 1), Col("Días", .5, "int"), Col("Haber básico", 1.1, "money"), Col("Bono antig.", 1), Col("H. extra y rec.", 1, "money"),
                   Col("Otros bonos", .9, "money"), Col("Total ganado", 1.2, "money"), Col("AFP laboral", 1.1, "money"), Col("ANS", .8, "money"), Col("RC-IVA", .9, "money"),
                   Col("Anticipos y otros", 1, "money"), Col("Total desc.", 1.1, "money"), Col("Líquido pagable", 1.2, "money")])
    tot = [0.0] * 11
    for i, d in enumerate(det, 1):
        afp = d["afp_vejez"] + d["afp_riesgo"] + d["afp_comision"] + d["afp_solidario"]
        ext = d["monto_extra"] + d["recargo_nocturno"] + d["dominical"]
        vals = [d["haber_basico"], d["bono_antig"], ext, d["otros_bonos"], d["total_ganado"], afp, d["ans"], d["rciva"], d["anticipos"] + d["otros_desc"], d["total_desc"], d["liquido"]]
        t.add(i, d["nombre"], d["ci"], d["dias"], *[round(v, 2) for v in vals])
        tot = [a + b for a, b in zip(tot, vals)]
    t.add("", "TOTALES", "", "", *[round(v, 2) for v in tot], estilo="total")
    return rep


@reporte("planilla_aportes", "Resumen de aportes laborales y patronales", MOD_RH, PERM, [MES()])
def planilla_aportes(ctx, p):
    pl, det = _plan(ctx, p)
    tt = ctx.rrhh.totales(pl["id"])
    rep = base(ctx, "Resumen de Aportes Laborales y Patronales", f"{mes_nombre(pl['mes'])} de {pl['anio']}")
    t = rep.tabla([Col("Concepto", 6), Col("Importe Bs", 1.6, "money")], titulo="Aportes del trabajador (descontados)")
    t.add("Cotización mensual - vejez", tt["afp_vejez"])
    t.add("Prima de riesgo común", tt["afp_riesgo"])
    t.add("Comisión Gestora Pública", tt["afp_comision"])
    t.add("Aporte solidario del asegurado", tt["afp_solidario"])
    t.add("Aporte Nacional Solidario (ANS)", tt["ans"])
    t.add("Total aportes laborales (Gestora Pública)", round(tt["afp_vejez"] + tt["afp_riesgo"] + tt["afp_comision"] + tt["afp_solidario"] + tt["ans"], 2), estilo="total")
    t2 = rep.tabla([Col("Concepto", 6), Col("Importe Bs", 1.6, "money")], titulo="Aportes patronales")
    t2.add("Caja Nacional de Salud (CNS)", tt["pat_cns"])
    t2.add("Prima de riesgo profesional", tt["pat_riesgo"])
    t2.add("Aporte patronal Pro-Vivienda", tt["pat_vivienda"])
    t2.add("Aporte patronal solidario", tt["pat_solidario"])
    if tt["pat_infocal"]:
        t2.add("INFOCAL", tt["pat_infocal"])
    t2.add("Total aportes patronales", round(tt["pat_cns"] + tt["pat_riesgo"] + tt["pat_vivienda"] + tt["pat_solidario"] + tt["pat_infocal"], 2), estilo="total")
    t3 = rep.tabla([Col("Concepto", 6), Col("Importe Bs", 1.6, "money")], titulo="Resumen")
    t3.add("Total ganado", tt["total_ganado"])
    t3.add("Costo patronal sobre el total ganado", round(tt["pat_cns"] + tt["pat_riesgo"] + tt["pat_vivienda"] + tt["pat_solidario"] + tt["pat_infocal"], 2))
    t3.add("Costo laboral total para la empresa", round(tt["total_ganado"] + tt["pat_cns"] + tt["pat_riesgo"] + tt["pat_vivienda"] + tt["pat_solidario"] + tt["pat_infocal"], 2), estilo="total")
    return rep


@reporte("planilla_rciva", "Planilla tributaria RC-IVA (dependientes)", MOD_RH, PERM, [MES()])
def planilla_rciva(ctx, p):
    pl, det = _plan(ctx, p)
    rep = base(ctx, "Planilla Tributaria - RC-IVA Dependientes", f"{mes_nombre(pl['mes'])} de {pl['anio']}", f"SMN Bs {pl['smn']:,.2f} - ingreso no imponible: 4 SMN", horizontal=True)
    t = rep.tabla([Col("Nº", .5, "int"), Col("Nombre", 3), Col("CI", 1), Col("Total ganado", 1.2, "money"), Col("Aportes AFP", 1.1, "money"), Col("Neto", 1.2, "money"), Col("Base imponible", 1.2, "money"),
                   Col("Impuesto 13%", 1.1, "money"), Col("Crédito 2 SMN", 1.1, "money"), Col("Crédito F-110", 1.1, "money"), Col("Saldo anterior", 1.1, "money"), Col("Mant. valor", 1, "money"),
                   Col("Retención a pagar", 1.1, "money"), Col("Saldo siguiente", 1.1, "money")])
    tot = [0.0] * 11
    for i, d in enumerate(det, 1):
        afp = d["afp_vejez"] + d["afp_riesgo"] + d["afp_comision"] + d["afp_solidario"]
        vals = [d["total_ganado"], afp, d["rc_neto"], d["rc_base"], d["rc_impuesto"], d["rc_cred_smn"], d["rc_facturas"], d["rc_saldo_ant"], d["rc_mant_valor"], d["rciva"], d["rc_saldo_sig"]]
        t.add(i, d["nombre"], d["ci"], *[round(v, 2) for v in vals])
        tot = [a + b for a, b in zip(tot, vals)]
    t.add("", "TOTALES", "", *[round(v, 2) for v in tot], estilo="total")
    return rep


@reporte("boletas_pago", "Boletas de pago", MOD_RH, PERM, [MES(), ParamDef("empleado", "Empleado (todos si vacío)", "empleado", None)])
def boletas(ctx, p):
    pl, det = _plan(ctx, p)
    rep = base(ctx, "Boletas de Pago", f"{mes_nombre(pl['mes'])} de {pl['anio']}", firmas=False)
    primero = True
    for d in det:
        if p.get("empleado") and int(p["empleado"]) != d["empleado_id"]:
            continue
        if not primero:
            rep.texto("", "salto")
        primero = False
        rep.texto(f"{d['nombre']}  -  CI {d['ci']}  -  {d['cargo'] or ''}  -  Ingreso: {fdate(d['fecha_ingreso'])}  -  Días trabajados: {d['dias']}", "titulo")
        t = rep.tabla([Col("Ingresos", 4), Col("Bs", 1.4, "money"), Col("Descuentos", 4), Col("Bs", 1.4, "money")])
        ing = [("Haber básico", d["haber_basico"]), ("Bono de antigüedad", d["bono_antig"]), ("Horas extra y recargos", d["monto_extra"] + d["recargo_nocturno"] + d["dominical"]), ("Otros bonos", d["otros_bonos"])]
        des = [("AFP - cotización vejez", d["afp_vejez"]), ("AFP - riesgo común", d["afp_riesgo"]), ("AFP - comisión", d["afp_comision"]), ("Aporte solidario", d["afp_solidario"]),
               ("Aporte nacional solidario", d["ans"]), ("RC-IVA", d["rciva"]), ("Anticipos", d["anticipos"]), ("Otros descuentos", d["otros_desc"])]
        for i in range(max(len(ing), len(des))):
            a = ing[i] if i < len(ing) else ("", None)
            b = des[i] if i < len(des) else ("", None)
            t.add(a[0], a[1] or None, b[0], b[1] or None)
        t.add("TOTAL GANADO", d["total_ganado"], "TOTAL DESCUENTOS", d["total_desc"], estilo="subtotal")
        t.add("LÍQUIDO PAGABLE", d["liquido"], "", None, estilo="total")
        rep.texto(monto_en_letras(d["liquido"]))
        rep.texto("\n\n_______________________________\nFirma del trabajador")
    return rep


@reporte("aguinaldo", "Aguinaldo de Navidad", MOD_RH, PERM)
def aguinaldo(ctx, p):
    rep = base(ctx, "Aguinaldo de Navidad", f"Gestión {ctx.gestion['anio']}", "Un sueldo promedio por 360 días trabajados (mínimo 3 meses de antigüedad)", horizontal=True)
    rep.firmas = ["Elaborado por", "Representante Legal"]
    t = rep.tabla([Col("Código", 1), Col("Nombre", 4), Col("CI", 1.2), Col("Ingreso", 1.1, "date"), Col("Días", .7, "int"), Col("Promedio ganado", 1.4, "money"), Col("Aguinaldo", 1.4, "money"), Col("2º aguinaldo", 1.4, "money"), Col("Total", 1.4, "money")])
    tot = [0.0] * 3
    for f in ctx.rrhh.aguinaldo(ctx.gestion["anio"]):
        t.add(f["codigo"], f["nombre"], f["ci"], fdate(f["ingreso"]), f["dias"], f["promedio"], f["aguinaldo"], f["segundo_aguinaldo"] or None, f["total"])
        tot = [tot[0] + f["aguinaldo"], tot[1] + f["segundo_aguinaldo"], tot[2] + f["total"]]
    t.add("", "TOTAL", "", "", "", "", round(tot[0], 2), round(tot[1], 2), round(tot[2], 2), estilo="total")
    return rep


@reporte("finiquito", "Finiquito de beneficios sociales", MOD_RH, PERM, [ParamDef("empleado", "Empleado", "empleado", requerido=True), ParamDef("fecha_retiro", "Fecha de retiro", "fecha", lambda c: c.fin),
                                                                       ParamDef("causal", "Causal", "lista", "RETIRO_VOLUNTARIO", [("RETIRO_VOLUNTARIO", "Retiro voluntario"), ("DESPIDO_INTEMPESTIVO", "Despido intempestivo / retiro forzoso")]),
                                                                       ParamDef("vacaciones", "Días de vacación pendientes", "entero", 0)])
def finiquito(ctx, p):
    f = ctx.rrhh.finiquito(int(p["empleado"]), p["fecha_retiro"], p["causal"], float(p["vacaciones"] or 0))
    e = f["empleado"]
    rep = base(ctx, "Finiquito de Beneficios Sociales", f"Fecha de retiro: {fdate(f['fecha_retiro'])}", f"{e['nombre']} - CI {e['ci']}  |  Antigüedad: {f['antiguedad']}", firmas=False)
    rep.firmas = ["Trabajador", "Empleador"]
    t = rep.tabla([Col("Concepto", 6), Col("Importe Bs", 1.6, "money")])
    t.add("Promedio de los últimos 3 meses (total ganado)", f["promedio"], estilo="subtotal")
    t.add("Indemnización por tiempo de servicios", f["indemnizacion"])
    t.add("Desahucio (3 meses)", f["desahucio"])
    t.add("Aguinaldo proporcional", f["aguinaldo_proporcional"])
    t.add("Vacaciones pendientes", f["vacaciones"])
    t.add("Sueldo pendiente del mes", f["sueldo_pendiente"])
    t.add("TOTAL BENEFICIOS SOCIALES", f["total"], estilo="total")
    rep.texto(monto_en_letras(f["total"]))
    rep.notas.append("Cálculo referencial según la Ley General del Trabajo; la liquidación definitiva debe ser validada por el Ministerio de Trabajo cuando corresponda.")
    return rep


@reporte("anticipos_sueldo", "Anticipos de sueldo", MOD_RH, PERM, [P_DESDE(), P_HASTA()])
def anticipos(ctx, p):
    rep = base(ctx, "Anticipos de Sueldo", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}")
    t = rep.tabla([Col("Fecha", 1.1, "date"), Col("Empleado", 4), Col("Monto", 1.4, "money"), Col("Descuento mensual", 1.4, "money"), Col("Saldo", 1.4, "money")])
    for a in ctx.db.query("SELECT a.*, e.nombre FROM anticipo a JOIN empleado e ON e.id=a.empleado_id WHERE a.fecha BETWEEN ? AND ? ORDER BY a.fecha", (str(p["desde"])[:10], str(p["hasta"])[:10])):
        t.add(fdate(a["fecha"]), a["nombre"], a["monto"], a["descuento_mes"], a["saldo"])
    return rep


@reporte("listado_empleados", "Listado de empleados", MOD_RH, PERM)
def listado_empleados(ctx, p):
    rep = base(ctx, "Listado de Empleados", firmas=False, horizontal=True)
    t = rep.tabla([Col("Código", .9), Col("Nombre", 3.5), Col("CI", 1.1), Col("Cargo", 2.5), Col("Ingreso", 1.1, "date"), Col("Haber básico", 1.3, "money"), Col("Bono de antigüedad", 1.3, "money"), Col("Estado", .9)])
    for e in ctx.rrhh.empleados(False):
        t.add(e["codigo"], e["nombre"], e["ci"], e["cargo"] or "", fdate(e["fecha_ingreso"]), e["haber_basico"], ctx.rrhh.bono_antiguedad(e["fecha_ingreso"], ctx.fin), "Activo" if e["activo"] else "Retirado")
    return rep
