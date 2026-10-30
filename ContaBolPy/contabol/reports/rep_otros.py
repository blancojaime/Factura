"""Activos fijos, costos y producción, administración."""
from __future__ import annotations

from ..util import fdate, mes_nombre
from .catalogo import MOD_ADM, MOD_AF, MOD_COS, P_DESDE, P_FECHA, P_HASTA, ParamDef, reporte
from .engine import Col, base


@reporte("cuadro_activos", "Cuadro de activos fijos", MOD_AF, "AF.REPORTES", [P_FECHA("Al")])
def cuadro_activos(ctx, p):
    rep = base(ctx, "Cuadro de Activos Fijos", f"Al {fdate(p['fecha'])}", horizontal=True)
    t = rep.tabla([Col("Código", 1), Col("Descripción", 4), Col("Alta", 1.1, "date"), Col("Valor original", 1.4, "money"), Col("Valor actualizado", 1.4, "money"), Col("Dep. acumulada", 1.4, "money"), Col("Valor neto", 1.4, "money"), Col("%", .7, "num", 1), Col("Estado", .8)])
    grupo, tot = None, [0.0] * 4
    sub = [0.0] * 4
    filas = ctx.activos.cuadro(p["fecha"])
    for a in filas:
        if a["grupo"] != grupo:
            if grupo is not None:
                t.add("", f"Subtotal {grupo}", "", *[round(x, 2) for x in sub], "", "", estilo="subtotal")
            grupo, sub = a["grupo"], [0.0] * 4
            t.add(a["grupo"].upper(), "", "", None, None, None, None, None, "", estilo="titulo")
        v = [a["valor_original"], a["valor_actual"], a["dep_acum"], a["valor_neto"]]
        t.add(a["codigo"], a["nombre"], fdate(a["fecha_alta"]), *v, a["pct"], "Activo" if a["estado"] == "A" else "Baja")
        sub = [x + y for x, y in zip(sub, v)]
        tot = [x + y for x, y in zip(tot, v)]
    if grupo is not None:
        t.add("", f"Subtotal {grupo}", "", *[round(x, 2) for x in sub], "", "", estilo="subtotal")
    t.add("", "TOTAL GENERAL", "", *[round(x, 2) for x in tot], "", "", estilo="total")
    return rep


@reporte("depreciacion_vista", "Depreciación del mes (vista previa)", MOD_AF, "AF.REPORTES", [ParamDef("mes", "Mes", "mes", 1)])
def depreciacion_vista(ctx, p):
    rep = base(ctx, "Depreciación de Activos Fijos", f"{mes_nombre(int(p['mes']))} de {ctx.gestion['anio']}", "Vista previa de la depreciación pendiente de registrar")
    t = rep.tabla([Col("Código", 1.1), Col("Activo", 4), Col("Grupo", 2.2), Col("Valor", 1.4, "money"), Col("Dep. acumulada", 1.4, "money"), Col("Depreciación del mes", 1.5, "money")])
    tot = 0.0
    for f in ctx.activos.depreciar(ctx.gestion["anio"], int(p["mes"]), registrar=False):
        t.add(f["codigo"], f["nombre"], f["grupo"], f["valor_actual"], f["dep_acum"], f["depreciacion"])
        tot += f["depreciacion"]
    t.add("", "TOTAL", "", "", "", round(tot, 2), estilo="total")
    return rep


@reporte("depreciacion_periodo", "Depreciaciones registradas", MOD_AF, "AF.REPORTES", [P_DESDE(), P_HASTA()])
def depreciacion_periodo(ctx, p):
    rep = base(ctx, "Depreciaciones Registradas", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}")
    t = rep.tabla([Col("Período", 1.1), Col("Código", 1.1), Col("Activo", 4), Col("Depreciación", 1.5, "money")])
    tot = 0.0
    for r in ctx.db.query("SELECT d.periodo, a.codigo, a.nombre, d.depreciacion FROM activo_dep d JOIN activo a ON a.id=d.activo_id WHERE d.fecha BETWEEN ? AND ? ORDER BY d.periodo, a.codigo",
                          (str(p["desde"])[:10], str(p["hasta"])[:10])):
        t.add(f"{r['periodo'][4:]}/{r['periodo'][:4]}", r["codigo"], r["nombre"], r["depreciacion"])
        tot += r["depreciacion"]
    t.add("", "", "TOTAL", round(tot, 2), estilo="total")
    return rep


@reporte("ordenes_produccion", "Órdenes de producción", MOD_COS, "COS.REPORTES")
def ordenes_produccion(ctx, p):
    rep = base(ctx, "Órdenes de Producción", f"Gestión {ctx.gestion['anio']}", horizontal=True)
    t = rep.tabla([Col("Nº", .6, "int"), Col("Fecha", 1.1, "date"), Col("Producto", 3.5), Col("Planificado", 1, "num"), Col("Producido", 1, "num"), Col("M. prima", 1.2, "money"), Col("M. obra", 1.2, "money"), Col("CIF", 1.2, "money"), Col("Costo total", 1.3, "money"), Col("Unitario", 1.1, "money"), Col("Estado", .9)])
    for o in ctx.produccion.listar():
        tot = o["costo_total"]
        t.add(o["numero"], fdate(o["fecha"]), f"{o['item_codigo']} {o['item_nombre']}", o["cant_plan"], o["cant_prod"], o["costo_mp"], o["costo_mod"], o["costo_cif"], tot,
              round(tot / o["cant_prod"], 2) if o["cant_prod"] else None, "Cerrada" if o["estado"] == "C" else "Abierta")
    return rep


@reporte("hoja_costos", "Hoja de costos de la orden", MOD_COS, "COS.REPORTES", [ParamDef("orden", "Orden de producción", "orden", requerido=True)])
def hoja_costos(ctx, p):
    o = ctx.produccion.obtener(int(p["orden"]))
    rep = base(ctx, f"Hoja de Costos - Orden Nº {o['numero']}", f"Fecha: {fdate(o['fecha'])}", f"{o['item_codigo']} {o['item_nombre']} - Planificado: {o['cant_plan']:g} - Producido: {o['cant_prod']:g}")
    rep.firmas = ["Jefe de Producción", "Contador"]
    t = rep.tabla([Col("Concepto", 5), Col("Cantidad / horas", 1.3, "num"), Col("Costo unitario", 1.3, "money"), Col("Importe Bs", 1.5, "money")], titulo="1. Materia prima directa")
    for m in o["mp"]:
        t.add(f"{m['codigo']} {m['nombre']}", m["cantidad"], m["costo_unit"], m["costo_total"])
    t.add("Subtotal materia prima", None, None, o["costo_mp"], estilo="subtotal")
    t2 = rep.tabla([Col("Concepto", 5), Col("Cantidad / horas", 1.3, "num"), Col("Costo unitario", 1.3, "money"), Col("Importe Bs", 1.5, "money")], titulo="2. Mano de obra directa")
    for m in o["mod"]:
        t2.add(m["descripcion"] or "Mano de obra", m["horas"], m["tarifa"], m["monto"])
    t2.add("Subtotal mano de obra", None, None, o["costo_mod"], estilo="subtotal")
    t3 = rep.tabla([Col("Concepto", 5), Col("", 1.3), Col("", 1.3), Col("Importe Bs", 1.5, "money")], titulo="3. Costos indirectos de fabricación")
    for m in o["cif"]:
        t3.add(m["concepto"], "", "", m["monto"])
    t3.add("Subtotal CIF", "", "", o["costo_cif"], estilo="subtotal")
    t4 = rep.tabla([Col("Resumen", 5), Col("", 1.3), Col("", 1.3), Col("Importe Bs", 1.5, "money")], titulo="Resumen de costos", sin_encabezado=True)
    t4.add("COSTO TOTAL DE PRODUCCIÓN", "", "", o["costo_total"], estilo="total")
    t4.add("Costo unitario", "", "", o["costo_unit"], estilo="subtotal")
    return rep


@reporte("auditoria", "Auditoría del sistema", MOD_ADM, "ADM.AUDITORIA", [P_DESDE(), P_HASTA()])
def auditoria(ctx, p):
    rep = base(ctx, "Auditoría del Sistema", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}", horizontal=True, firmas=False)
    t = rep.tabla([Col("Fecha y hora", 1.8), Col("Usuario", 1.1), Col("Módulo", 1.3), Col("Acción", 1.6), Col("Detalle", 5), Col("Equipo", 1.2)])
    for a in ctx.sistema.auditoria(p["desde"], p["hasta"]):
        t.add(a["fecha"].replace("T", " "), a["login"] or "", a["modulo"] or "", a["accion"] or "", a["detalle"] or "", a["equipo"] or "")
    return rep


@reporte("usuarios_permisos", "Usuarios del sistema", MOD_ADM, "ADM.USUARIOS")
def usuarios(ctx, p):
    rep = base(ctx, "Usuarios del Sistema", firmas=False)
    t = rep.tabla([Col("Usuario", 1.5), Col("Nombre", 4), Col("Rol", 1.5), Col("Estado", 1), Col("Último acceso", 2)])
    for u in ctx.sistema.listar_usuarios():
        t.add(u["login"], u["nombre"], ctx.sistema.rol(u["id"], ctx.empresa["id"]) or ("ADMIN" if u["es_admin"] else ""), "Activo" if u["activo"] else "Inactivo", (u["ultimo_acceso"] or "").replace("T", " "))
    return rep
