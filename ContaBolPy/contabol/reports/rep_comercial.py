"""Informes comerciales: clientes, proveedores, ventas, compras, cobros y pagos."""
from __future__ import annotations

from datetime import date

from ..util import fdate, iso, monto_en_letras, r2, to_date
from .catalogo import MOD_COM, P_DESDE, P_FECHA, P_HASTA, ParamDef, reporte
from .engine import Col, base

PERM = "COM.REPORTES"
CLASE = lambda: ParamDef("clase", "Clase", "lista", "C", [("C", "Clientes (por cobrar)"), ("P", "Proveedores (por pagar)")])  # noqa: E731


def _per(p):
    return f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}"


@reporte("saldos_terceros", "Saldos por cobrar / por pagar", MOD_COM, PERM, [CLASE()])
def saldos_terceros(ctx, p):
    rep = base(ctx, "Saldos por Cobrar" if p["clase"] == "C" else "Saldos por Pagar", f"Al {fdate(ctx.fin)}")
    t = rep.tabla([Col("Código", 1.2), Col("Nombre", 5), Col("NIT", 1.3), Col("Docs.", .6, "int"), Col("Total documentos", 1.5, "money"), Col("Saldo", 1.5, "money")])
    tot = 0.0
    for r in ctx.terceros.saldos(p["clase"]):
        t.add(r["codigo"], r["nombre"], r["nit"], r["documentos"], r["facturado"], r["saldo"])
        tot += r["saldo"]
    t.add("", "TOTAL", "", "", "", round(tot, 2), estilo="total")
    return rep


@reporte("kardex_tercero", "Estado de cuenta de cliente / proveedor", MOD_COM, PERM, [CLASE(), ParamDef("tercero", "Cliente / proveedor", "tercero", requerido=True), P_DESDE(), P_HASTA()])
def kardex_tercero(ctx, p):
    t_ = ctx.terceros.obtener(int(p["tercero"]))
    rep = base(ctx, "Estado de Cuenta", _per(p), f"{t_['nombre']} - NIT {t_['nit'] or 's/n'}")
    t = rep.tabla([Col("Fecha", 1.1, "date"), Col("Documento", 2), Col("Referencia", 1.4), Col("Cargos", 1.4, "money"), Col("Abonos", 1.4, "money"), Col("Saldo", 1.4, "money")])
    for f in ctx.cobros.estado_cuenta(t_["id"], p["clase"], p["desde"], p["hasta"]):
        t.add(fdate(f["fecha"]), f["doc"], f["ref"] or "", f["cargo"] or None, f["abono"] or None, f["saldo"])
    return rep


@reporte("antiguedad_saldos", "Antigüedad de saldos", MOD_COM, PERM, [CLASE(), P_FECHA("Al")])
def antiguedad(ctx, p):
    tabla = "venta" if p["clase"] == "C" else "compra"
    corte = to_date(p["fecha"])
    rep = base(ctx, "Antigüedad de Saldos", f"Al {fdate(corte)}", "Por cobrar" if p["clase"] == "C" else "Por pagar", horizontal=True)
    t = rep.tabla([Col("Cliente / proveedor", 4), Col("Corriente", 1.3, "money"), Col("1-30 días", 1.3, "money"), Col("31-60 días", 1.3, "money"), Col("61-90 días", 1.3, "money"), Col("Más de 90", 1.3, "money"), Col("Total", 1.4, "money")])
    acum: dict[str, list[float]] = {}
    for d in ctx.db.query(f"SELECT d.saldo, d.vencimiento, d.fecha, t.nombre FROM {tabla} d JOIN tercero t ON t.id=d.tercero_id WHERE d.estado='V' AND d.saldo>0.004"):
        v = to_date(d["vencimiento"] or d["fecha"])
        dias = (corte - v).days
        k = 0 if dias <= 0 else 1 if dias <= 30 else 2 if dias <= 60 else 3 if dias <= 90 else 4
        a = acum.setdefault(d["nombre"], [0.0] * 5)
        a[k] += d["saldo"]
    tot = [0.0] * 5
    for n in sorted(acum):
        a = acum[n]
        t.add(n, *[round(x, 2) for x in a], round(sum(a), 2))
        tot = [x + y for x, y in zip(tot, a)]
    t.add("TOTAL", *[round(x, 2) for x in tot], round(sum(tot), 2), estilo="total")
    return rep


@reporte("documentos_pendientes", "Notas pendientes de cobro / pago", MOD_COM, PERM, [CLASE()])
def pendientes(ctx, p):
    srv = ctx.ventas if p["clase"] == "C" else ctx.compras
    rep = base(ctx, "Documentos Pendientes de Cobro" if p["clase"] == "C" else "Documentos Pendientes de Pago", f"Al {fdate(ctx.fin)}", horizontal=True)
    t = rep.tabla([Col("Nº", .7, "int"), Col("Fecha", 1.1, "date"), Col("Vence", 1.1, "date"), Col("Cliente / proveedor", 4), Col("Factura", 1.1), Col("Total", 1.3, "money"), Col("Saldo", 1.3, "money")])
    tot = 0.0
    for d in srv.listar(pendientes=True):
        t.add(d["numero"], fdate(d["fecha"]), fdate(d["vencimiento"]), d["tercero"], d["nro_factura"] or "", d["total"], d["saldo"])
        tot += d["saldo"]
    t.add("", "", "", "TOTAL", "", "", round(tot, 2), estilo="total")
    return rep


@reporte("listado_terceros", "Listado de clientes / proveedores", MOD_COM, PERM, [CLASE()])
def listado_terceros(ctx, p):
    rep = base(ctx, "Listado de Clientes" if p["clase"] == "C" else "Listado de Proveedores", firmas=False, horizontal=True)
    t = rep.tabla([Col("Código", 1), Col("Nombre", 4), Col("NIT", 1.2), Col("Teléfono", 1.2), Col("Dirección", 3.5), Col("Email", 2.5), Col("Límite crédito", 1.2, "money")])
    for r in ctx.terceros.listar(p["clase"]):
        t.add(r["codigo"], r["nombre"], r["nit"], r["telefono"] or "", r["direccion"] or "", r["email"] or "", r["limite_credito"] or None)
    return rep


def _docs(ctx, p, srv, titulo):
    rep = base(ctx, titulo, _per(p), horizontal=True)
    t = rep.tabla([Col("Nº", .7, "int"), Col("Fecha", 1.1, "date"), Col("Cliente / proveedor", 4), Col("Pago", .8), Col("Factura", 1.1), Col("Subtotal", 1.3, "money"), Col("Desc.", 1, "money"), Col("Total", 1.3, "money"), Col("Saldo", 1.3, "money"), Col("Estado", .9)])
    tt = ts = 0.0
    for d in srv.listar(p["desde"], p["hasta"]):
        t.add(d["numero"], fdate(d["fecha"]), d["tercero"], d["tipo_pago"], d["nro_factura"] or "", d["subtotal"], d["descuento"], d["total"], d["saldo"], "Anulada" if d["estado"] == "A" else "Vigente")
        if d["estado"] == "V":
            tt += d["total"]
            ts += d["saldo"]
    t.add("", "", "TOTALES (vigentes)", "", "", "", "", round(tt, 2), round(ts, 2), "", estilo="total")
    return rep


@reporte("ventas_periodo", "Ventas del período", MOD_COM, PERM, [P_DESDE(), P_HASTA()])
def ventas_periodo(ctx, p):
    return _docs(ctx, p, ctx.ventas, "Ventas del Período")


@reporte("compras_periodo", "Compras del período", MOD_COM, PERM, [P_DESDE(), P_HASTA()])
def compras_periodo(ctx, p):
    return _docs(ctx, p, ctx.compras, "Compras del Período")


@reporte("cobros_pagos", "Cobros y pagos del período", MOD_COM, PERM, [P_DESDE(), P_HASTA(), ParamDef("clase", "Clase", "lista", "CO", [("CO", "Cobros"), ("PA", "Pagos")])])
def cobros_pagos(ctx, p):
    rep = base(ctx, "Cobros del Período" if p["clase"] == "CO" else "Pagos del Período", _per(p))
    t = rep.tabla([Col("Nº", .7, "int"), Col("Fecha", 1.1, "date"), Col("Cliente / proveedor", 4), Col("Forma", .8), Col("Importe", 1.4, "money"), Col("Estado", .9)])
    tot = 0.0
    for c in ctx.cobros.listar(p["clase"], p["desde"], p["hasta"]):
        t.add(c["numero"], fdate(c["fecha"]), c["tercero"], c["forma"], c["monto"], "Anulado" if c["estado"] == "A" else "Vigente")
        if c["estado"] == "V":
            tot += c["monto"]
    t.add("", "", "TOTAL", "", round(tot, 2), "", estilo="total")
    return rep


def _ranking(ctx, p, sql, titulo, col, primeros):
    rep = base(ctx, titulo, _per(p))
    t = rep.tabla([Col("#", .5, "int"), Col(col, 5), Col("Cantidad / docs.", 1.3, "num"), Col("Importe Bs", 1.6, "money")])
    for i, r in enumerate(ctx.db.query(sql, (iso(p["desde"]), iso(p["hasta"]), int(p["top"]))), 1):
        t.add(i, r["nombre"], r["cant"], r["imp"])
    return rep


TOP = lambda: ParamDef("top", "Mostrar los primeros", "entero", 20)  # noqa: E731


@reporte("mas_vendidos", "Productos más vendidos", MOD_COM, PERM, [P_DESDE(), P_HASTA(), TOP()])
def mas_vendidos(ctx, p):
    return _ranking(ctx, p, "SELECT i.codigo||' '||i.nombre AS nombre, SUM(d.cantidad) AS cant, SUM(d.total) AS imp FROM venta_det d JOIN venta v ON v.id=d.venta_id JOIN item i ON i.id=d.item_id "
                    "WHERE v.estado='V' AND v.fecha BETWEEN ? AND ? GROUP BY i.id ORDER BY imp DESC LIMIT ?", "Productos más Vendidos", "Producto", 20)


@reporte("mas_comprados", "Productos más comprados", MOD_COM, PERM, [P_DESDE(), P_HASTA(), TOP()])
def mas_comprados(ctx, p):
    return _ranking(ctx, p, "SELECT i.codigo||' '||i.nombre AS nombre, SUM(d.cantidad) AS cant, SUM(d.total) AS imp FROM compra_det d JOIN compra v ON v.id=d.compra_id JOIN item i ON i.id=d.item_id "
                    "WHERE v.estado='V' AND v.fecha BETWEEN ? AND ? GROUP BY i.id ORDER BY imp DESC LIMIT ?", "Productos más Comprados", "Producto", 20)


@reporte("mejores_clientes", "Mejores clientes", MOD_COM, PERM, [P_DESDE(), P_HASTA(), TOP()])
def mejores_clientes(ctx, p):
    return _ranking(ctx, p, "SELECT t.nombre, COUNT(*) AS cant, SUM(v.total) AS imp FROM venta v JOIN tercero t ON t.id=v.tercero_id WHERE v.estado='V' AND v.fecha BETWEEN ? AND ? "
                    "GROUP BY t.id ORDER BY imp DESC LIMIT ?", "Mejores Clientes", "Cliente", 20)


@reporte("mejores_proveedores", "Mejores proveedores", MOD_COM, PERM, [P_DESDE(), P_HASTA(), TOP()])
def mejores_proveedores(ctx, p):
    return _ranking(ctx, p, "SELECT t.nombre, COUNT(*) AS cant, SUM(v.total) AS imp FROM compra v JOIN tercero t ON t.id=v.tercero_id WHERE v.estado='V' AND v.fecha BETWEEN ? AND ? "
                    "GROUP BY t.id ORDER BY imp DESC LIMIT ?", "Mejores Proveedores", "Proveedor", 20)


@reporte("comisiones", "Comisiones de vendedores", MOD_COM, PERM, [P_DESDE(), P_HASTA()])
def comisiones(ctx, p):
    rep = base(ctx, "Comisiones de Vendedores", _per(p))
    t = rep.tabla([Col("Vendedor", 4), Col("Ventas Bs", 1.5, "money"), Col("% comisión", 1, "pct"), Col("Comisión Bs", 1.5, "money")])
    tot = 0.0
    for r in ctx.db.query("SELECT w.nombre, w.comision, COALESCE(SUM(v.total),0) AS ventas FROM vendedor w LEFT JOIN venta v ON v.vendedor_id=w.id AND v.estado='V' AND v.fecha BETWEEN ? AND ? "
                          "GROUP BY w.id ORDER BY w.nombre", (iso(p["desde"]), iso(p["hasta"]))):
        c = r2(r["ventas"] * r["comision"] / 100)
        t.add(r["nombre"], r["ventas"], r["comision"], c)
        tot += c
    t.add("TOTAL", None, None, round(tot, 2), estilo="total")
    return rep


def _nota(ctx, p, srv, titulo):
    d = srv.obtener(int(p["id"]))
    rep = base(ctx, f"{titulo} Nº {d['numero']}", f"Fecha: {fdate(d['fecha'])}", f"{d['tercero']['nombre']} - NIT {d['tercero']['nit'] or 's/n'}", firmas=False)
    rep.firmas = ["Entregué conforme", "Recibí conforme"]
    t = rep.tabla([Col("Código", 1.2), Col("Descripción", 5), Col("Cantidad", 1.1, "num"), Col("Precio", 1.2, "money"), Col("Desc.", 1, "money"), Col("Importe", 1.4, "money")])
    for i in d["items"]:
        t.add(i["codigo"], i["nombre"], i["cantidad"], i["precio"], i["descuento"] or None, i["total"])
    t.add("", "", "", "", "Subtotal", d["subtotal"], estilo="subtotal")
    if d["descuento"]:
        t.add("", "", "", "", "Descuento", -d["descuento"])
    if d["recargo"]:
        t.add("", "", "", "", "Recargo", d["recargo"])
    t.add("", "", "", "", "TOTAL Bs", d["total"], estilo="total")
    rep.texto(monto_en_letras(d["total"]))
    rep.texto(f"Condición: {'Contado' if d['tipo_pago'] == 'CON' else 'Crédito'}" + (f" - Factura Nº {d['nro_factura']}" if d["nro_factura"] else "") + (f" - Estado: ANULADA" if d["estado"] == "A" else ""))
    return rep


@reporte("nota_venta", "Nota de venta (impresión)", MOD_COM, PERM, [ParamDef("id", "Nº interno de la venta", "entero", requerido=True)])
def nota_venta(ctx, p):
    return _nota(ctx, p, ctx.ventas, "Nota de Venta")


@reporte("nota_compra", "Nota de compra (impresión)", MOD_COM, PERM, [ParamDef("id", "Nº interno de la compra", "entero", requerido=True)])
def nota_compra(ctx, p):
    return _nota(ctx, p, ctx.compras, "Nota de Compra")
