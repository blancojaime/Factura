"""Informes de inventarios."""
from __future__ import annotations

from ..util import fdate, iso, r2
from .catalogo import MOD_INV, P_BOOL, P_DESDE, P_FECHA, P_HASTA, ParamDef, reporte
from .engine import Col, base

PERM = "INV.REPORTES"


@reporte("listado_items", "Listado de ítems", MOD_INV, PERM, [P_BOOL("solo_activos", "Solo ítems activos", True)])
def listado_items(ctx, p):
    rep = base(ctx, "Listado de Ítems", firmas=False, horizontal=True)
    t = rep.tabla([Col("Código", 1.3), Col("Descripción", 5), Col("Grupo", 2), Col("Unidad", .8), Col("Precio venta", 1.3, "money"), Col("Costo prom.", 1.3, "num", 4), Col("Stock", 1.2, "num", 2), Col("Mínimo", 1, "num", 2)])
    for i in ctx.inventario.items(solo_activos=p["solo_activos"]):
        t.add(i["codigo"], i["nombre"], i["grupo"] or "", i["unidad"] or "", i["precio_venta"], i["costo_prom"], i["stock"], i["stock_min"])
    return rep


@reporte("kardex_item", "Kardex físico valorado", MOD_INV, PERM, [ParamDef("item", "Ítem", "item", requerido=True), P_DESDE(), P_HASTA()])
def kardex_item(ctx, p):
    k = ctx.inventario.kardex(int(p["item"]), p["desde"], p["hasta"])
    it = k["item"]
    rep = base(ctx, "Kardex Físico Valorado", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}", f"{it['codigo']} - {it['nombre']}  (método: costo promedio ponderado)", horizontal=True)
    t = rep.tabla([Col("Fecha", 1.1, "date"), Col("Almacén", .9), Col("Detalle", 3), Col("Ent. cant.", 1, "num"), Col("Sal. cant.", 1, "num"), Col("Costo unit.", 1.1, "num", 4),
                   Col("Entradas Bs", 1.2, "money"), Col("Salidas Bs", 1.2, "money"), Col("Saldo cant.", 1.1, "num"), Col("Saldo Bs", 1.3, "money")])
    t.add("", "", "SALDO INICIAL", None, None, None, None, None, k["saldo_inicial_cant"], k["saldo_inicial_val"], estilo="subtotal")
    for f in k["filas"]:
        t.add(fdate(f["fecha"]), f["almacen"], f["detalle"] or f["tipo"], f["ent_cant"] or None, f["sal_cant"] or None, f["costo_unit"], f["ent_val"] or None, f["sal_val"] or None, f["saldo_cant"], f["saldo_val"])
    return rep


@reporte("existencias", "Existencias valoradas", MOD_INV, PERM, [P_FECHA("Al"), ParamDef("almacen", "Almacén (todos si vacío)", "almacen", None)])
def existencias(ctx, p):
    rep = base(ctx, "Inventario Valorado", f"Al {fdate(p['fecha'])}", horizontal=True)
    t = rep.tabla([Col("Código", 1.3), Col("Descripción", 5), Col("Grupo", 2), Col("Unidad", .8), Col("Cantidad", 1.2, "num"), Col("Costo unit.", 1.3, "num", 4), Col("Valor Bs", 1.5, "money")])
    tot = 0.0
    for f in ctx.inventario.existencias(p["fecha"], int(p["almacen"]) if p.get("almacen") else None):
        t.add(f["codigo"], f["nombre"], f["grupo"] or "", f["unidad"] or "", f["cantidad"], f["costo_unit"], f["valor"])
        tot += f["valor"]
    t.add("", "TOTAL INVENTARIO", "", "", "", "", round(tot, 2), estilo="total")
    return rep


@reporte("sugerencia_compras", "Sugerencia de compras (stock mínimo)", MOD_INV, PERM)
def sugerencia_compras(ctx, p):
    rep = base(ctx, "Sugerencia de Compras", "Ítems por debajo del stock mínimo", firmas=False)
    t = rep.tabla([Col("Código", 1.3), Col("Descripción", 5), Col("Stock", 1.2, "num"), Col("Mínimo", 1.2, "num"), Col("Sugerido", 1.2, "num")])
    for i in ctx.inventario.items():
        if not i["es_servicio"] and i["stock_min"] > 0 and i["stock"] < i["stock_min"]:
            t.add(i["codigo"], i["nombre"], i["stock"], i["stock_min"], r2(i["stock_min"] * 2 - i["stock"]))
    return rep


@reporte("por_vencer", "Productos vencidos y por vencer", MOD_INV, PERM, [P_FECHA("Vencen hasta")])
def por_vencer(ctx, p):
    rep = base(ctx, "Productos Vencidos y por Vencer", f"Con vencimiento hasta el {fdate(p['fecha'])}", firmas=False)
    t = rep.tabla([Col("Código", 1.3), Col("Descripción", 4), Col("Almacén", 1), Col("Lote", 1.2), Col("Vence", 1.1, "date"), Col("Cantidad", 1.2, "num")])
    for r in ctx.inventario.por_vencer(p["fecha"]):
        t.add(r["codigo"], r["nombre"], r["almacen"], r["lote"], fdate(r["vencimiento"]), r["cantidad"])
    return rep


@reporte("lista_precios", "Lista de precios", MOD_INV, PERM)
def lista_precios(ctx, p):
    rep = base(ctx, "Lista de Precios", f"Vigente al {fdate(ctx.fin)}", firmas=False)
    t = rep.tabla([Col("Código", 1.3), Col("Descripción", 5), Col("Unidad", .8), Col("Precio de venta Bs", 1.6, "money")])
    for i in ctx.inventario.items():
        t.add(i["codigo"], i["nombre"], i["unidad"] or "", i["precio_venta"])
    return rep


@reporte("movimientos_inventario", "Movimientos de inventario", MOD_INV, PERM, [P_DESDE(), P_HASTA()])
def movimientos(ctx, p):
    rep = base(ctx, "Movimientos de Inventario", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}")
    t = rep.tabla([Col("Nº", .7, "int"), Col("Fecha", 1.1, "date"), Col("Tipo", 1), Col("Almacén", 2), Col("Glosa", 4), Col("Valor Bs", 1.4, "money"), Col("Estado", .9)])
    for m in ctx.inventario.movimientos(p["desde"], p["hasta"]):
        t.add(m["numero"], fdate(m["fecha"]), m["tipo"], m["almacen"], m["glosa"] or "", m["total"], "Anulado" if m["estado"] == "A" else "Vigente")
    return rep
