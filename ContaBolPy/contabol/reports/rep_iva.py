"""Impuestos: libros de compras y ventas (LCV), liquidación de IVA e IT."""
from __future__ import annotations

from ..util import fdate, mes_nombre
from .catalogo import MOD_IVA, P_BOOL, ParamDef, reporte
from .engine import Col, base

PERM = "IVA.REPORTES"


def P_PER_D(): return ParamDef("mes_desde", "Desde el mes", "mes", 1)
def P_PER_H(): return ParamDef("mes_hasta", "Hasta el mes", "mes", lambda c: 12)


def _libro(ctx, p, libro: str):
    nombre = "Compras" if libro == "C" else "Ventas"
    rep = base(ctx, f"Libro de {nombre} IVA", f"Del mes {int(p['mes_desde']):02d} al {int(p['mes_hasta']):02d} de {ctx.gestion['anio']}",
               "Registro de " + ("compras" if libro == "C" else "ventas") + " (Ley 843 - RND vigente)", horizontal=True)
    rep.notas.append("Estado: V = válida, A = anulada, E = extraviada, N = no utilizada, C = emitida en contingencia. Las facturas no válidas se muestran con importes en cero.")
    if libro == "C":
        cols = [Col("Nº", .5, "int"), Col("Fecha", 1, "date"), Col("NIT proveedor", 1.2), Col("Razón social", 3), Col("Nº factura", 1), Col("DUI/DIM", .8), Col("Nº autorización / CUF", 2),
                Col("Importe total", 1.2, "money"), Col("No sujeto CF", 1, "money"), Col("Subtotal", 1.2, "money"), Col("Descuentos", 1, "money"), Col("Base CF", 1.2, "money"),
                Col("Crédito fiscal", 1.1, "money"), Col("Tipo", .5, "int"), Col("Est.", .5)]
    else:
        cols = [Col("Nº", .5, "int"), Col("Fecha", 1, "date"), Col("NIT/CI cliente", 1.2), Col("Razón social", 3), Col("Nº factura", 1), Col("Nº autorización / CUF", 2),
                Col("Importe total", 1.2, "money"), Col("No sujeto IVA", 1, "money"), Col("Exportac. y exentos", 1.1, "money"), Col("Tasa cero", .9, "money"), Col("Subtotal", 1.2, "money"),
                Col("Descuentos", 1, "money"), Col("Base DF", 1.2, "money"), Col("Débito fiscal", 1.1, "money"), Col("Est.", .5)]
    t = rep.tabla(cols)
    tot = [0.0] * 8
    n = 0
    for mes in range(int(p["mes_desde"]), int(p["mes_hasta"]) + 1):
        for f in ctx.iva.listar(libro, ctx.gestion["anio"], mes):
            n += 1
            if libro == "C":
                t.add(n, fdate(f["fecha"]), f["nit"], f["razon_social"], f["nro_factura"], f["dui"] or "", f["nro_autorizacion"], f["importe_total"], f["no_sujeto"],
                      f["subtotal"], f["descuentos"], f["base_iva"], f["iva"], f["tipo_compra"], f["estado"])
                vals = [f["importe_total"], f["no_sujeto"], f["subtotal"], f["descuentos"], f["base_iva"], f["iva"]]
            else:
                t.add(n, fdate(f["fecha"]), f["nit"], f["razon_social"], f["nro_factura"], f["nro_autorizacion"], f["importe_total"], f["no_sujeto"], f["exento"],
                      f["tasa_cero"], f["subtotal"], f["descuentos"], f["base_iva"], f["iva"], f["estado"])
                vals = [f["importe_total"], f["no_sujeto"], f["exento"], f["tasa_cero"], f["subtotal"], f["descuentos"], f["base_iva"], f["iva"]]
            for i, v in enumerate(vals):
                tot[i] += v
    if libro == "C":
        t.add("", "", "", "TOTALES", "", "", "", *[round(x, 2) for x in tot[:6]], "", "", estilo="total")
    else:
        t.add("", "", "", "TOTALES", "", "", *[round(x, 2) for x in tot[:8]], "", estilo="total")
    return rep


@reporte("libro_compras", "Libro de compras IVA", MOD_IVA, PERM, [P_PER_D(), P_PER_H()])
def libro_compras(ctx, p):
    return _libro(ctx, p, "C")


@reporte("libro_ventas", "Libro de ventas IVA", MOD_IVA, PERM, [P_PER_D(), P_PER_H()])
def libro_ventas(ctx, p):
    return _libro(ctx, p, "V")


@reporte("resumen_iva", "Liquidación mensual de IVA e IT", MOD_IVA, PERM, [ParamDef("mes_hasta", "Hasta el mes", "mes", lambda c: 12)])
def resumen_iva(ctx, p):
    rep = base(ctx, "Liquidación de IVA e IT", f"Gestión {ctx.gestion['anio']} (Form. 200 y 400)", horizontal=True)
    t = rep.tabla([Col("Mes", 1.4), Col("Ventas facturadas", 1.4, "money"), Col("Débito fiscal", 1.3, "money"), Col("Compras facturadas", 1.4, "money"), Col("Crédito fiscal", 1.3, "money"),
                   Col("Saldo anterior", 1.3, "money"), Col("Mant. valor (UFV)", 1.2, "money"), Col("IVA a pagar", 1.3, "money"), Col("Saldo a favor", 1.3, "money"), Col("IT devengado", 1.3, "money")])
    tot = [0.0] * 4
    for m in range(1, int(p["mes_hasta"]) + 1):
        r = ctx.iva.resumen_mensual(ctx.gestion["anio"], m)
        t.add(mes_nombre(m), r["ventas_facturadas"], r["debito_fiscal"], r["compras_facturadas"], r["credito_fiscal"], r["saldo_anterior"], r["mant_valor"], r["iva_a_pagar"], r["saldo_favor"], r["it_devengado"])
        tot[0] += r["debito_fiscal"]
        tot[1] += r["credito_fiscal"]
        tot[2] += r["iva_a_pagar"]
        tot[3] += r["it_devengado"]
    t.add("TOTAL", None, round(tot[0], 2), None, round(tot[1], 2), None, None, round(tot[2], 2), None, round(tot[3], 2), estilo="total")
    rep.notas.append("El IVA se paga hasta el vencimiento según el último dígito del NIT (Form. 200); el IT (Form. 400) se paga por separado. El crédito no usado se actualiza con la variación de la UFV.")
    return rep


@reporte("lcv_exportacion", "Exportación LCV (formato de carga al SIN)", MOD_IVA, PERM, [ParamDef("libro", "Libro", "lista", "V", [("V", "Ventas"), ("C", "Compras")]), ParamDef("mes", "Mes", "mes", lambda c: 1)])
def lcv_exportacion(ctx, p):
    libro = p["libro"]
    rep = base(ctx, f"Archivo LCV - {'Ventas' if libro == 'V' else 'Compras'}", f"Período {int(p['mes']):02d}/{ctx.gestion['anio']}", horizontal=True, firmas=False)
    rep.notas.append("Estructura de columnas para carga en el módulo de Registro de Compras y Ventas. Verifique contra la RND vigente antes de enviar.")
    cols = [Col(c, 1.2) for c in ("Nº", "Fecha", "NIT", "Razón social", "Nº factura", "CUF/Autorización", "Importe total", "No sujeto", "Subtotal", "Descuentos", "Base", "IVA", "Estado")]
    t = rep.tabla(cols)
    for i, f in enumerate(ctx.iva.listar(libro, ctx.gestion["anio"], int(p["mes"])), 1):
        t.add(i, fdate(f["fecha"]), f["nit"], f["razon_social"], f["nro_factura"], f["nro_autorizacion"], f"{f['importe_total']:.2f}", f"{f['no_sujeto']:.2f}",
              f"{f['subtotal']:.2f}", f"{f['descuentos']:.2f}", f"{f['base_iva']:.2f}", f"{f['iva']:.2f}", f["estado"])
    return rep


@reporte("facturas_anuladas", "Facturas anuladas / no utilizadas", MOD_IVA, PERM)
def facturas_anuladas(ctx, p):
    rep = base(ctx, "Facturas Anuladas y No Utilizadas", f"Gestión {ctx.gestion['anio']}", firmas=False)
    t = rep.tabla([Col("Libro", .8), Col("Fecha", 1.1, "date"), Col("Nº factura", 1.2), Col("Razón social", 4), Col("Estado", 1)])
    for f in ctx.db.query("SELECT * FROM factura WHERE estado<>'V' ORDER BY fecha"):
        t.add("Ventas" if f["libro"] == "V" else "Compras", fdate(f["fecha"]), f["nro_factura"], f["razon_social"], {"A": "Anulada", "E": "Extraviada", "N": "No utilizada", "C": "Contingencia"}.get(f["estado"], f["estado"]))
    return rep
