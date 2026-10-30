"""Informes de contabilidad general."""
from __future__ import annotations

from ..util import fdate, mes_nombre, to_date
from .catalogo import MOD_CONT, P_BOOL, P_DESDE, P_FECHA, P_HASTA, P_MES, P_MONEDA, P_NIVEL, ParamDef, reporte
from .engine import Col, base

PERM = "CONT.REPORTES"


def _per(p):
    return f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}"


@reporte("plan_cuentas", "Plan de cuentas", MOD_CONT, PERM, [P_NIVEL(), P_BOOL("solo_mov", "Solo cuentas de movimiento")])
def plan_cuentas(ctx, p):
    rep = base(ctx, "Plan de Cuentas", f"Hasta nivel {p['nivel']}", firmas=False)
    t = rep.tabla([Col("Código", 2), Col("Cuenta", 6), Col("Nivel", .7, "int"), Col("Mov.", .6), Col("Naturaleza", 1.1), Col("M.E.", .6)])
    for c in ctx.cuentas.listar():
        if c["nivel"] > int(p["nivel"]) or (p["solo_mov"] and not c["es_movimiento"]):
            continue
        t.add(c["codigo"], c["nombre"], c["nivel"], "Sí" if c["es_movimiento"] else "", "Deudora" if c["naturaleza"] == "D" else "Acreedora",
              "Sí" if c["moneda_extranjera"] else "", estilo="" if c["es_movimiento"] else "grupo", nivel=0)
    return rep


@reporte("libro_diario", "Libro diario", MOD_CONT, PERM, [P_DESDE(), P_HASTA(), P_MONEDA()])
def libro_diario(ctx, p):
    rep = base(ctx, "Libro Diario", _per(p), moneda=p["moneda"], horizontal=True)
    t = rep.tabla([Col("Fecha", 1.1, "date"), Col("Comprobante", 1.3), Col("Cuenta", 2.2), Col("Detalle", 4), Col("Debe", 1.4, "money"), Col("Haber", 1.4, "money")])
    ult = None
    td = th = 0.0
    for r in ctx.libros.diario(p["desde"], p["hasta"], p["moneda"]):
        if r["comprobante_id"] != ult:
            ult = r["comprobante_id"]
            cod = f"{r['tipo']}-{r['mes']:02d}/{r['numero']:04d}"
            t.add(fdate(r["fecha"]), cod, "", r["glosa_cab"], None, None, estilo="grupo")
        t.add("", "", r["cuenta_codigo"], f"{r['cuenta_nombre']}" + (f" - {r['glosa']}" if r["glosa"] else ""), r["debe"] or None, r["haber"] or None)
        td += r["debe"]
        th += r["haber"]
    t.add("", "", "", "TOTALES", round(td, 2), round(th, 2), estilo="total")
    return rep


@reporte("libro_mayor", "Libro mayor de una cuenta", MOD_CONT, PERM, [ParamDef("cuenta", "Cuenta", "cuenta", requerido=True), P_DESDE(), P_HASTA(), P_MONEDA()])
def libro_mayor(ctx, p):
    m = ctx.libros.mayor(int(p["cuenta"]), p["desde"], p["hasta"], p["moneda"])
    c = m["cuenta"]
    rep = base(ctx, "Libro Mayor", _per(p), f"Cuenta {c['codigo']} - {c['nombre']}", p["moneda"], horizontal=True)
    t = rep.tabla([Col("Fecha", 1.1, "date"), Col("Comprobante", 1.4), Col("Cuenta", 1.8), Col("Glosa", 4), Col("Debe", 1.3, "money"), Col("Haber", 1.3, "money"), Col("Saldo", 1.4, "money")])
    t.add("", "", "", "SALDO ANTERIOR", None, None, m["saldo_anterior"], estilo="subtotal")
    for f in m["filas"]:
        t.add(fdate(f["fecha"]), f"{f['tipo']}-{f['mes']:02d}/{f['numero']:04d}", f["cuenta_codigo"], f["glosa"], f["debe"] or None, f["haber"] or None, f["saldo"])
    t.add("", "", "", "TOTALES Y SALDO FINAL", m["total_debe"], m["total_haber"], m["saldo_final"], estilo="total")
    return rep


@reporte("mayor_general", "Libro mayor (varias cuentas)", MOD_CONT, PERM, [ParamDef("cod_desde", "Desde la cuenta (código)", "texto", "1"), ParamDef("cod_hasta", "Hasta la cuenta (código)", "texto", "5.9"), P_DESDE(), P_HASTA()])
def mayor_general(ctx, p):
    rep = base(ctx, "Libro Mayor General", _per(p), horizontal=True)
    t = rep.tabla([Col("Cuenta", 2), Col("Nombre", 5), Col("Saldo anterior", 1.5, "money"), Col("Debe", 1.5, "money"), Col("Haber", 1.5, "money"), Col("Saldo final", 1.5, "money")])
    for c in ctx.cuentas.listar(solo_movimiento=True):
        if not (p["cod_desde"] <= c["codigo"] <= p["cod_hasta"] + "~"):
            continue
        m = ctx.libros.mayor(c["id"], p["desde"], p["hasta"])
        if not m["filas"] and abs(m["saldo_anterior"]) < 0.005:
            continue
        t.add(c["codigo"], c["nombre"], m["saldo_anterior"], m["total_debe"], m["total_haber"], m["saldo_final"])
    return rep


@reporte("sumas_saldos", "Balance de sumas y saldos", MOD_CONT, PERM, [P_DESDE(), P_HASTA(), P_NIVEL(), P_MONEDA(), P_BOOL("solo_con_saldo", "Omitir cuentas sin movimiento", True)])
def sumas_saldos(ctx, p):
    rep = base(ctx, "Balance de Sumas y Saldos", _per(p), moneda=p["moneda"], horizontal=True)
    t = rep.tabla([Col("Código", 2), Col("Cuenta", 5), Col("Sumas Debe", 1.5, "money"), Col("Sumas Haber", 1.5, "money"), Col("Saldo Deudor", 1.5, "money"), Col("Saldo Acreedor", 1.5, "money")])
    td = th = sd = sh = 0.0
    for f in ctx.libros.sumas_saldos(p["desde"], p["hasta"], int(p["nivel"]), p["moneda"], p["solo_con_saldo"]):
        debe = f["debe"] + f["saldo_ini_d"]
        haber = f["haber"] + f["saldo_ini_h"]
        t.add(f["codigo"], f["nombre"], debe, haber, f["saldo_d"] or None, f["saldo_h"] or None, estilo="" if f["es_movimiento"] else "grupo", nivel=0)
        if f["es_movimiento"]:
            td += debe
            th += haber
            sd += f["saldo_d"]
            sh += f["saldo_h"]
    t.add("", "TOTALES", round(td, 2), round(th, 2), round(sd, 2), round(sh, 2), estilo="total")
    return rep


@reporte("hoja_trabajo", "Hoja de trabajo (8 columnas)", MOD_CONT, PERM, [P_DESDE(), P_HASTA()])
def hoja_trabajo(ctx, p):
    rep = base(ctx, "Hoja de Trabajo", _per(p), horizontal=True)
    t = rep.tabla([Col("Código", 1.8), Col("Cuenta", 4), Col("Sumas Debe", 1.3, "money"), Col("Sumas Haber", 1.3, "money"), Col("Saldo Deudor", 1.3, "money"),
                   Col("Saldo Acreedor", 1.3, "money"), Col("Resultados Pérd.", 1.3, "money"), Col("Resultados Gan.", 1.3, "money"), Col("Balance Activo", 1.3, "money"), Col("Balance Pas.+Pat.", 1.3, "money")])
    tot = [0.0] * 8
    for f in ctx.libros.sumas_saldos(p["desde"], p["hasta"], 9):
        if not f["es_movimiento"]:
            continue
        deb, hab = f["debe"] + f["saldo_ini_d"], f["haber"] + f["saldo_ini_h"]
        sd, sh = f["saldo_d"], f["saldo_h"]
        res_p = sd if f["tipo"] in ("I", "G") else 0.0
        res_g = sh if f["tipo"] in ("I", "G") else 0.0
        b_a = sd if f["tipo"] in ("A", "P", "T") else 0.0
        b_p = sh if f["tipo"] in ("A", "P", "T") else 0.0
        fila = [deb, hab, sd, sh, res_p, res_g, b_a, b_p]
        for i, v in enumerate(fila):
            tot[i] += v
        t.add(f["codigo"], f["nombre"], *[v or None for v in fila])
    t.add("", "SUBTOTALES", *[round(v, 2) for v in tot], estilo="total")
    util = round(tot[5] - tot[4], 2)
    t.add("", "Utilidad (pérdida) del período", None, None, None, None, util if util > 0 else None, -util if util < 0 else None, -util if util < 0 else None, util if util > 0 else None, estilo="subtotal")
    return rep


@reporte("lista_comprobantes", "Listado de comprobantes", MOD_CONT, PERM, [P_DESDE(), P_HASTA(), ParamDef("tipo", "Tipo", "tipo_comp", ""), P_BOOL("incluir_anulados", "Incluir anulados")])
def lista_comprobantes(ctx, p):
    rep = base(ctx, "Listado de Comprobantes", _per(p), horizontal=True)
    t = rep.tabla([Col("Comprobante", 1.4), Col("Fecha", 1.1, "date"), Col("Tipo", 1.2), Col("Glosa", 5), Col("A nombre de", 2), Col("Debe Bs", 1.3, "money"), Col("Haber Bs", 1.3, "money"), Col("Estado", .9)])
    td = th = 0.0
    for c in ctx.vouchers.listar(p["desde"], p["hasta"], p.get("tipo") or None):
        if c["estado"] == "A" and not p["incluir_anulados"]:
            continue
        t.add(ctx.vouchers.codigo(c), fdate(c["fecha"]), c["tipo_nombre"], c["glosa"], c["a_nombre"] or "", c["debe_bs"], c["haber_bs"], "Anulado" if c["estado"] == "A" else "Vigente")
        if c["estado"] == "V":
            td += c["debe_bs"]
            th += c["haber_bs"]
    t.add("", "", "", "TOTALES (vigentes)", "", round(td, 2), round(th, 2), "", estilo="total")
    return rep


def _comprobante_rep(ctx, c, rep=None, primero=True):
    from .engine import ReporteDef
    rep = rep or base(ctx, f"Comprobante {ctx.vouchers.codigo(c)}", f"Fecha: {fdate(c['fecha'])}", c["glosa"], firmas=False)
    rep.firmas = ["Elaborado por", "Revisado por", "Aprobado por", "Recibí conforme"]
    t = rep.tabla([Col("Cuenta", 2), Col("Nombre de la cuenta", 4), Col("Detalle", 3), Col("Debe Bs", 1.4, "money"), Col("Haber Bs", 1.4, "money"), Col("Debe $us", 1.2, "money"), Col("Haber $us", 1.2, "money")])
    for l in c["lineas"]:
        t.add(l["cuenta_codigo"], l["cuenta_nombre"], l["glosa"] or "", l["debe_bs"] or None, l["haber_bs"] or None, l["debe_usd"] or None, l["haber_usd"] or None)
    t.add("", "", "TOTAL", c["debe_bs"], c["haber_bs"], round(sum(l["debe_usd"] for l in c["lineas"]), 2), round(sum(l["haber_usd"] for l in c["lineas"]), 2), estilo="total")
    if c.get("a_nombre"):
        rep.texto(f"Pagado a / recibido de: {c['a_nombre']}" + (f"    Doc.: {c['nro_doc']}" if c.get("nro_doc") else ""))
    rep.texto(f"T.C.: {c['tc']:.2f}    Estado: {'ANULADO' if c['estado'] == 'A' else 'Vigente'}")
    return rep


@reporte("comprobante", "Comprobante (impresión)", MOD_CONT, PERM, [ParamDef("id", "Comprobante", "comprobante", requerido=True)])
def comprobante(ctx, p):
    return _comprobante_rep(ctx, ctx.vouchers.obtener(int(p["id"])))


@reporte("comprobantes_rango", "Reimpresión de comprobantes por rango", MOD_CONT, PERM, [P_DESDE(), P_HASTA(), ParamDef("tipo", "Tipo", "tipo_comp", "")])
def comprobantes_rango(ctx, p):
    rep = base(ctx, "Comprobantes", _per(p), firmas=False)
    first = True
    for c in ctx.vouchers.listar(p["desde"], p["hasta"], p.get("tipo") or None, estado="V"):
        if not first:
            rep.texto("", "salto")
        first = False
        rep.texto(f"COMPROBANTE {ctx.vouchers.codigo(c)} - {fdate(c['fecha'])} - {c['glosa']}", "titulo")
        _comprobante_rep(ctx, ctx.vouchers.obtener(c["id"]), rep)
    return rep


@reporte("libreta_banco", "Libreta bancaria", MOD_CONT, PERM, [ParamDef("cuenta", "Cuenta de banco/caja", "cuenta", requerido=True), P_DESDE(), P_HASTA()])
def libreta_banco(ctx, p):
    return _mayor_titulo(ctx, p, "Libreta Bancaria")


def _mayor_titulo(ctx, p, titulo):
    m = ctx.libros.mayor(int(p["cuenta"]), p["desde"], p["hasta"])
    c = m["cuenta"]
    rep = base(ctx, titulo, _per(p), f"{c['codigo']} - {c['nombre']}", horizontal=True)
    t = rep.tabla([Col("Fecha", 1.1, "date"), Col("Comprobante", 1.4), Col("Nº doc.", 1.2), Col("Detalle", 4), Col("Ingresos", 1.3, "money"), Col("Egresos", 1.3, "money"), Col("Saldo", 1.4, "money")])
    t.add("", "", "", "SALDO ANTERIOR", None, None, m["saldo_anterior"], estilo="subtotal")
    for f in m["filas"]:
        t.add(fdate(f["fecha"]), f"{f['tipo']}-{f['mes']:02d}/{f['numero']:04d}", "", f["glosa"], f["debe"] or None, f["haber"] or None, f["saldo"])
    t.add("", "", "", "TOTALES", m["total_debe"], m["total_haber"], m["saldo_final"], estilo="total")
    return rep


@reporte("conciliacion", "Conciliación bancaria", MOD_CONT, PERM, [ParamDef("cuenta", "Cuenta de banco", "cuenta", requerido=True), P_FECHA("Al"), ParamDef("saldo_extracto", "Saldo según extracto", "importe", 0.0)])
def conciliacion(ctx, p):
    c = ctx.bancos.conciliacion(int(p["cuenta"]), p["fecha"], float(p["saldo_extracto"] or 0) if p.get("saldo_extracto") else None)
    rep = base(ctx, "Conciliación Bancaria", f"Al {fdate(p['fecha'])}", f"{c['cuenta']['codigo']} - {c['cuenta']['nombre']}")
    t = rep.tabla([Col("Concepto", 6), Col("Importe", 1.6, "money")])
    t.add("Saldo según libros", c["saldo_libros"], estilo="subtotal")
    t.add("Menos: depósitos en tránsito (no registrados por el banco)", -c["depositos_transito"])
    t.add("Más: cheques y cargos pendientes de cobro", c["cheques_circulacion"])
    t.add("Saldo bancario calculado", c["saldo_banco_calculado"], estilo="total")
    if c["saldo_extracto"] is not None:
        t.add("Saldo según extracto bancario", c["saldo_extracto"])
        t.add("DIFERENCIA", c["diferencia"], estilo="total")
    d = rep.tabla([Col("Fecha", 1.1, "date"), Col("Comprobante", 1.3), Col("Detalle", 5), Col("Depósitos", 1.4, "money"), Col("Cheques/cargos", 1.4, "money")], titulo="Movimientos no conciliados")
    for x in c["pendientes"]:
        d.add(fdate(x["fecha"]), f"{x['tipo']}-{x['numero']}", x["glosa"], x["debe"] or None, x["haber"] or None)
    return rep


@reporte("presupuesto", "Presupuesto asignado", MOD_CONT, PERM)
def presupuesto(ctx, p):
    rep = base(ctx, "Presupuesto Asignado", "Por cuenta y mes", horizontal=True, firmas=False)
    t = rep.tabla([Col("Cuenta", 3.5)] + [Col(mes_nombre(m)[:3], 1, "money", 0) for m in range(1, 13)] + [Col("Total", 1.3, "money", 0)])
    for r in ctx.db.query("SELECT DISTINCT c.id, c.codigo, c.nombre FROM presupuesto p JOIN cuenta c ON c.id=p.cuenta_id WHERE p.monto<>0 ORDER BY c.codigo"):
        m = ctx.presupuesto.obtener(r["id"])
        t.add(f"{r['codigo']} {r['nombre']}", *m, sum(m))
    return rep


@reporte("ejecucion_presupuesto", "Ejecución presupuestaria", MOD_CONT, PERM, [ParamDef("mes_desde", "Desde el mes", "mes", 1), ParamDef("mes_hasta", "Hasta el mes", "mes", lambda c: 12)])
def ejecucion_presupuesto(ctx, p):
    rep = base(ctx, "Ejecución Presupuestaria", f"Meses {p['mes_desde']} a {p['mes_hasta']}")
    t = rep.tabla([Col("Cuenta", 5), Col("Presupuesto", 1.5, "money"), Col("Ejecutado", 1.5, "money"), Col("Saldo", 1.5, "money"), Col("% ejec.", 1, "pct")])
    for r in ctx.presupuesto.ejecucion(int(p["mes_desde"]), int(p["mes_hasta"])):
        t.add(f"{r['codigo']} {r['nombre']}", r["presupuesto"], r["ejecutado"], r["saldo"], r["pct"])
    return rep


@reporte("gastos_centros", "Gastos por centro de costo", MOD_CONT, PERM, [P_DESDE(), P_HASTA()])
def gastos_centros(ctx, p):
    rep = base(ctx, "Gastos por Centro de Costo", _per(p))
    t = rep.tabla([Col("Centro de costo", 3), Col("Cuenta", 5), Col("Importe Bs", 1.5, "money")])
    rows = ctx.db.query("SELECT COALESCE(cc.codigo||' '||cc.nombre,'(sin centro)') AS centro, c.codigo||' '||c.nombre AS cuenta, SUM(d.debe_bs-d.haber_bs) AS imp "
                        "FROM comp_det d JOIN comprobante k ON k.id=d.comprobante_id JOIN cuenta c ON c.id=d.cuenta_id LEFT JOIN centro_costo cc ON cc.id=d.centro_id "
                        "WHERE k.estado='V' AND k.origen<>'CIERRE' AND c.tipo='G' AND k.fecha BETWEEN ? AND ? GROUP BY centro, cuenta HAVING ABS(imp)>0.004 ORDER BY centro, cuenta",
                        (to_date(p["desde"]).isoformat(), to_date(p["hasta"]).isoformat()))
    for r in rows:
        t.add(r["centro"], r["cuenta"], r["imp"])
    t.add("", "TOTAL", round(sum(r["imp"] for r in rows), 2), estilo="total")
    return rep


@reporte("tipos_cambio", "Tipos de cambio y UFV", MOD_CONT, PERM, [P_DESDE(), P_HASTA()])
def tipos_cambio(ctx, p):
    rep = base(ctx, "Tipos de Cambio y UFV", _per(p), firmas=False)
    t = rep.tabla([Col("Fecha", 1.5, "date"), Col("Dólar (Bs)", 1.5, "num", 4), Col("UFV", 1.5, "num", 5)])
    for r in ctx.tc.listar(p["desde"], p["hasta"]):
        t.add(fdate(r["fecha"]), r["dolar"], r["ufv"])
    return rep


@reporte("indices", "Índices financieros", MOD_CONT, PERM, [P_FECHA("Al")])
def indices(ctx, p):
    b = ctx.estados.balance_general(p["fecha"], 3)
    er = ctx.estados.estado_resultados(ctx.inicio, p["fecha"], 3)
    val = {f["codigo"]: f["importe"] for f in b["filas"] if f.get("codigo")}
    ac, pc = val.get("1.1", 0.0), val.get("2.1", 0.0)
    inv = val.get("1.1.3", 0.0)
    disp = val.get("1.1.1", 0.0)
    rep = base(ctx, "Índices Financieros", f"Al {fdate(p['fecha'])}", firmas=False)
    t = rep.tabla([Col("Índice", 4), Col("Fórmula", 5), Col("Resultado", 1.5, "num")])
    div = lambda a, b_: round(a / b_, 2) if b_ else 0.0  # noqa: E731
    t.add("Liquidez corriente", "Activo corriente / Pasivo corriente", div(ac, pc))
    t.add("Prueba ácida", "(Activo corriente - Inventarios) / Pasivo corriente", div(ac - inv, pc))
    t.add("Capital de trabajo (Bs)", "Activo corriente - Pasivo corriente", round(ac - pc, 2))
    t.add("Disponibilidad inmediata", "Disponible / Pasivo corriente", div(disp, pc))
    t.add("Endeudamiento total", "Total pasivo / Total activo", div(b["total_pasivo"], b["total_activo"]))
    t.add("Solvencia patrimonial", "Total patrimonio / Total activo", div(b["total_patrimonio"], b["total_activo"]))
    t.add("Margen bruto", "Utilidad bruta / Ventas netas", div(er["utilidad_bruta"], er["ventas"]))
    t.add("Margen neto", "Resultado neto / Ventas netas", div(er["neto"], er["ventas"]))
    t.add("Rentabilidad sobre patrimonio (ROE)", "Resultado neto / Patrimonio", div(er["neto"], b["total_patrimonio"]))
    return rep
