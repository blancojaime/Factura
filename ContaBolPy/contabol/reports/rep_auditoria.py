"""Informes de los módulos de auditoría financiera (MAF) y tributaria (MAI)."""
from __future__ import annotations

import json

from ..util import fdate
from .catalogo import ParamDef, reporte
from .engine import Col, base

MOD_MAF, MOD_MAI = "Auditoría financiera (MAF)", "Auditoría tributaria (MAI)"
P_ENC = lambda: ParamDef("encargo", "Encargo de auditoría", "encargo", None, requerido=True)
NIV = {"B": "Bajo", "M": "Medio", "A": "Alto"}
EST_PASO = {"P": "Pendiente", "E": "En ejecución", "R": "Realizado", "N": "No aplica"}


def _cab(ctx, p, titulo, horizontal=True):
    e = ctx.auditoria.encargo(int(p["encargo"]))
    rep = base(ctx, titulo, f"{fdate(e['periodo_ini'])} al {fdate(e['periodo_fin'])}", f"{e['codigo']} · {e['nombre']}", horizontal=horizontal)
    rep.firmas = ["Preparado por", "Revisado por", "Socio responsable"]
    if e["estado"] == "CERRADO":
        rep.notas.append(f"Encargo CERRADO el {e['cerrado_en']} por {e['cerrado_por']}. Huella SHA-256: {e['sha256']}")
    return e, rep


@reporte("aud_mpa", "Memorándum de planificación (MPA)", MOD_MAF, "AUD.REPORTES", [P_ENC()])
def aud_mpa(ctx, p):
    e, rep = _cab(ctx, p, "Memorándum de Planificación de Auditoría", False)
    a = ctx.auditoria
    m, mat = a.memorando(e["id"]), a.materialidad(e["id"])
    for tit, key in (("1. Términos del encargo", "terminos"), ("2. Comprensión del negocio y del sector", "negocio"), ("3. Control interno", "control_interno"), ("4. Normativa aplicable", "normativa_aplicable")):
        rep.texto(tit, "titulo")
        rep.texto(m[key] or "(pendiente de completar)")
    rep.texto("5. Modelo de riesgo de auditoría: RA = RI × RC × RD", "titulo")
    t = rep.tabla([Col("Componente", 3), Col("Valor", 1.2)])
    t.add("Riesgo inherente (RI)", NIV[m["riesgo_inherente"]]).add("Riesgo de control (RC)", NIV[m["riesgo_control"]]).add("Riesgo de auditoría aceptable (RA)", f"{m['riesgo_auditoria_aceptable']:.2%}")
    t.add("Riesgo de detección (RD)", f"{m['riesgo_deteccion']:.2%}", estilo="total")
    rep.texto(a.interpretar_rd(m["riesgo_deteccion"]), "nota")
    if mat:
        rep.texto("6. Materialidad", "titulo")
        t = rep.tabla([Col("Concepto", 3), Col("%", .8, "num", 2), Col("Importe", 1.5, "money")])
        t.add(f"Base: {mat['base']}", None, mat["valor_base"]).add("Materialidad global", mat["pct_global"], mat["materialidad_global"], estilo="total")
        t.add("Materialidad de desempeño", mat["pct_desempeno"], mat["materialidad_desempeno"]).add("Umbral de cuestiones triviales", mat["pct_trivial"], mat["umbral_trivial"])
        rep.texto(mat["justificacion"] or "", "nota")
    return rep


@reporte("aud_riesgos", "Matriz de riesgos por aseveración", MOD_MAF, "AUD.REPORTES", [P_ENC()])
def aud_riesgos(ctx, p):
    e, rep = _cab(ctx, p, "Matriz de Riesgos por Aseveración")
    t = rep.tabla([Col("Prog.", .6), Col("Componente", 2), Col("Aseveración", 2), Col("Riesgo", 3.5), Col("Nivel", .8), Col("Respuesta de auditoría", 4)])
    for r in ctx.auditoria.riesgos(e["id"]):
        t.add(r["programa_ref"], r["componente"], r["aseveracion"], r["descripcion"], NIV[r["nivel"]], r["respuesta"])
    return rep


@reporte("aud_programas", "Programas de auditoría", MOD_MAF, "AUD.REPORTES", [P_ENC()])
def aud_programas(ctx, p):
    e, rep = _cab(ctx, p, "Programas de Auditoría por Componente")
    t = rep.tabla([Col("Nº", .5), Col("Procedimiento", 6), Col("Aseveración", 1.8), Col("Base", 1.4), Col("Estado", 1.1), Col("Ref. PT", .8), Col("Resp.", .6), Col("Conclusión", 3)])
    for pr in ctx.auditoria.programas(e["id"]):
        t.add(pr["indice"], f"{pr['componente'].upper()} — {pr['objetivo']}", "", "", "", "", "", "", estilo="titulo")
        for s in pr["pasos"]:
            t.add(s["nro"], s["procedimiento"], s["aseveracion"], s["base_normativa"], EST_PASO[s["estado"]], s["referencia_pt"] or "", s["responsable"] or "", s["conclusion"] or "")
    av = ctx.auditoria.avance(e["id"])
    rep.notas.append(f"Avance: {av['hechos']} de {av['total']} procedimientos ({av['pct']} %).")
    return rep


@reporte("aud_sumarias", "Cédulas sumarias y analíticas", MOD_MAF, "AUD.REPORTES", [P_ENC(), ParamDef("analiticas", "Incluir analíticas", "bool", True)])
def aud_sumarias(ctx, p):
    e, rep = _cab(ctx, p, "Cédulas Sumarias y Analíticas")
    t = rep.tabla([Col("Índice", .8), Col("Rubro / cuenta", 5), Col("Saldo según sistema", 1.5, "money"), Col("Ajustes", 1.2, "money"), Col("Reclasif.", 1.2, "money"), Col("Saldo auditado", 1.5, "money"), Col("Marcas", 1), Col("Prep./Rev.", 1)])
    a = ctx.auditoria
    for s in a.sumarias(e["id"]):
        t.add(s["indice"], s["titulo"], s["saldo_sistema"], s["ajustes"], s["reclasificaciones"], s["saldo_auditado"], "", f"{s['preparado_por'] or '—'}/{s['revisado_por'] or '—'}", estilo="subtotal")
        if p.get("analiticas"):
            for an in a.analiticas(s["id"]):
                t.add(an["indice"], f"{an['cuenta_codigo']}  {an['concepto']}", an["saldo_libros"], None, None, an["saldo_verificado"], an["marcas"] or "", "", nivel=1)
    leyenda = "; ".join(f"{m['simbolo']} = {m['significado']}" for m in _marcas(ctx, e["id"]))
    rep.notas.append("Leyenda de marcas: " + leyenda)
    return rep


def _marcas(ctx, eid):
    return ctx.db.query("SELECT * FROM marca_auditoria WHERE encargo_id=? ORDER BY id", (eid,))


@reporte("aud_pruebas", "Pruebas sustantivas ejecutadas", MOD_MAF, "AUD.REPORTES", [P_ENC()])
def aud_pruebas(ctx, p):
    e, rep = _cab(ctx, p, "Pruebas Sustantivas Ejecutadas")
    for pr in ctx.auditoria.pruebas(e["id"]):
        d = pr["datos"]
        rep.texto(f"{pr['indice_pt']} · {pr['titulo']} — {'CONFORME' if pr['conforme'] else 'CON DIFERENCIAS'} (ejecutó {pr['ejecutado_por']}, {pr['ejecutado_en'][:10]})", "titulo")
        res = d.get("resumen") or {}
        if res:
            t = rep.tabla([Col("Indicador", 4), Col("Valor", 2)])
            for k, v in res.items():
                t.add(str(k).replace("_", " "), f"{v:,.2f}" if isinstance(v, float) else str(v))
        rep.texto(d.get("conclusion", ""), "nota")
    return rep


@reporte("aud_hallazgos", "Hallazgos de auditoría", MOD_MAF, "AUD.REPORTES", [P_ENC()])
def aud_hallazgos(ctx, p):
    e, rep = _cab(ctx, p, "Hallazgos de Auditoría (Condición, Criterio, Causa y Efecto)")
    t = rep.tabla([Col("Cód.", .6), Col("Condición", 3), Col("Criterio", 2.5), Col("Causa", 2), Col("Efecto", 2), Col("Recomendación", 2.5), Col("Descargo de la Gerencia", 2.5), Col("Nivel", .7), Col("Impacto Bs", 1.1, "money")])
    for h in ctx.auditoria.hallazgos(e["id"]):
        t.add(h["codigo"], h["condicion"], h["criterio"], h["causa"], h["efecto"], h["recomendacion"] or "", h["descargo_gerencia"] or "Sin descargo", NIV[h["nivel"]], h["impacto_monto"])
    return rep


@reporte("aud_desvios", "Resumen de desvíos y ajustes propuestos", MOD_MAF, "AUD.REPORTES", [P_ENC()])
def aud_desvios(ctx, p):
    e, rep = _cab(ctx, p, "Cédula de Resumen de Desvíos y Ajustes Propuestos")
    r = ctx.auditoria.resumen_desvios(e["id"])
    t = rep.tabla([Col("Nº", .5, "int"), Col("Tipo", .6), Col("Descripción", 5), Col("Estado", 1.4), Col("Efecto en resultados", 1.6, "money")])
    for a in r["ajustes"]:
        t.add(a["numero"], a["tipo"], a["descripcion"], a["estado"].replace("_", " ").title(), a["efecto_resultado"])
        for l in a["lineas"]:
            t.add("", "", f"      {l['codigo']}  {l['nombre']}   Debe {l['debe']:,.2f} / Haber {l['haber']:,.2f}", "", None)
    t2 = rep.tabla([Col("Concepto", 4), Col("Importe", 1.6, "money")], "Evaluación frente a la materialidad")
    t2.add("Ajustes ACEPTADOS (efecto en resultados)", r["efecto_aceptados"]).add("Desvíos NO CORREGIDOS (efecto en resultados)", r["efecto_no_corregidos"])
    t2.add("No corregidos por encima del umbral trivial (acumulado absoluto)", r["no_corregidos_no_triviales"])
    t2.add("Materialidad de desempeño", r["materialidad_desempeno"]).add("Materialidad global", r["materialidad_global"], estilo="total")
    rep.texto("Conclusión: " + r["veredicto"], "nota")
    return rep


@reporte("aud_dictamen", "Dictamen / informe emitido", MOD_MAF, "AUD.REPORTES", [P_ENC()])
def aud_dictamen(ctx, p):
    e, rep = _cab(ctx, p, "Dictamen e Informes de Auditoría", False)
    ds = ctx.auditoria.dictamenes(e["id"])
    if not ds:
        rep.texto("Aún no se ha emitido ningún dictamen o informe.", "nota")
    for d in ds:
        rep.texto(f"{d['clase']} {('· ' + d['opinion']) if d['opinion'] else ''} — {d['fecha']}", "titulo")
        for par in (d["texto"] or "").split("\n\n"):
            rep.texto(par)
    return rep


@reporte("aud_trail", "Bitácora de auditoría (pista de trabajo)", MOD_MAF, "AUD.REPORTES", [P_ENC()])
def aud_trail(ctx, p):
    e, rep = _cab(ctx, p, "Bitácora de Auditoría (usuario, fecha y huella encadenada)")
    t = rep.tabla([Col("Fecha", 1.6), Col("Usuario", 1), Col("Entidad", 1.4), Col("Acción", 1.2), Col("Detalle", 5), Col("Huella (SHA-256)", 2.2)])
    for r in ctx.db.query("SELECT * FROM auditoria_trail WHERE encargo_id=? ORDER BY id", (e["id"],)):
        t.add(r["fecha"].replace("T", " "), r["usuario"], r["entidad"], r["accion"], r["detalle"] or "", r["hash"][:20] + "…")
    rep.notas.append("Integridad de la cadena de huellas: " + ("CORRECTA" if ctx.auditoria.verificar_trail() else "ALTERADA"))
    return rep


# ---------------------------------------------------------------- MAI
@reporte("aud_iva_it", "Conciliación Débito/Crédito Fiscal e IT", MOD_MAI, "AUD.REPORTES", [P_ENC()])
def aud_iva_it(ctx, p):
    e, rep = _cab(ctx, p, "Conciliación del Débito Fiscal, Crédito Fiscal e IT")
    r = ctx.aud_trib.conciliacion_iva_it(e["id"])
    t = rep.tabla([Col("Período", 1.4), Col("Ventas libro", 1.3, "money"), Col("Ventas sistema", 1.3, "money"), Col("DF libro", 1.1, "money"), Col("DF contab.", 1.1, "money"), Col("Dif. DF", .9, "money"),
                   Col("CF libro", 1.1, "money"), Col("CF contab.", 1.1, "money"), Col("Dif. CF", .9, "money"), Col("IT teórico", 1, "money"), Col("IT contab.", 1, "money"), Col("Dif. IT", .9, "money")])
    for f in r["filas"]:
        t.add(f["periodo"], f["ventas_libro"], f["ventas_sistema"], f["df_libro"], f["df_contabilidad"], f["dif_df"], f["cf_libro"], f["cf_contabilidad"], f["dif_cf"], f["it_teorico"], f["it_contabilidad"], f["dif_it"])
    rep.texto(r["conclusion"], "nota")
    return rep


@reporte("aud_bancarizacion", "Bancarización", MOD_MAI, "AUD.REPORTES", [P_ENC()])
def aud_bancarizacion(ctx, p):
    e, rep = _cab(ctx, p, "Operaciones sujetas a Bancarización")
    r = ctx.aud_trib.bancarizacion(e["id"])
    t = rep.tabla([Col("Clase", .9), Col("Fecha", 1, "date"), Col("Factura", 1), Col("Razón social", 3), Col("NIT", 1.2), Col("Importe", 1.3, "money"), Col("Medio de pago", 1.3), Col("Estado", 1.8)])
    for f in r["filas"]:
        t.add(f["clase"], f["fecha"], f["factura"], f["proveedor_cliente"], f["nit"], f["importe"], f["medio"], f["estado"])
    rep.texto(r["titulo"] + ". " + r["conclusion"], "nota")
    return rep


@reporte("aud_iue", "Depuración de gastos e IUE", MOD_MAI, "AUD.REPORTES", [P_ENC()])
def aud_iue(ctx, p):
    e, rep = _cab(ctx, p, "Cédula de Depuración de Gastos y Determinación del IUE")
    r = ctx.aud_trib.cedula_iue(e["id"])
    t = rep.tabla([Col("Concepto", 5), Col("Importe", 1.6, "money")])
    for f in r["filas"]:
        t.add(f["concepto"], f["importe"], estilo="total" if "imponible" in f["concepto"] or "IUE" in f["concepto"] else "")
    t2 = rep.tabla([Col("Cuenta", 1.2), Col("Concepto", 3), Col("Motivo", 4), Col("Base legal", 2), Col("Monto", 1.3, "money"), Col("Estado", 1.2)], "Gastos no deducibles")
    for g in r["gastos"]:
        t2.add(g["cuenta_codigo"] or "", g["concepto"], g["motivo"], g["base_legal"] or "", g["monto"], g["estado"].title())
    rep.texto(r["conclusion"], "nota")
    return rep


@reporte("aud_anexos_itc", "Anexos de la Información Tributaria Complementaria", MOD_MAI, "AUD.REPORTES", [P_ENC()])
def aud_anexos(ctx, p):
    e, rep = _cab(ctx, p, "Anexos de la Información Tributaria Complementaria (ITC)")
    rep.texto("Formatos referenciales generados con datos del sistema; deben adecuarse al formato oficial del SIN vigente antes de su presentación.", "nota")
    for a in ctx.aud_trib.anexos(e["id"]):
        rep.texto(f"Anexo {a['numero']}. {a['titulo']}", "titulo")
        datos = a["datos"]
        if not datos:
            rep.texto("Sin datos.", "nota")
            continue
        claves = [k for k in datos[0].keys() if k not in ("nivel", "estilo", "codigo_fila", "extra")][:6]
        t = rep.tabla([Col(k.replace("_", " ").title(), 3 if isinstance(datos[0][k], str) else 1.3, "txt" if not isinstance(datos[0][k], (int, float)) else "money") for k in claves])
        for f in datos[:200]:
            t.add(*[f.get(k) for k in claves])
    return rep


@reporte("aud_contingencias", "Situación tributaria y contingencias", MOD_MAI, "AUD.REPORTES", [P_ENC(), ParamDef("sancion", "Sanción (%) a aplicar", "importe", 0.0)])
def aud_contingencias(ctx, p):
    e, rep = _cab(ctx, p, "Situación Tributaria y Liquidación de Contingencias (Ley 2492)")
    r = ctx.aud_trib.situacion_tributaria(e["id"], sancion_pct=float(p.get("sancion") or 0))
    t = rep.tabla([Col("Hallazgo", .8), Col("Concepto", 5), Col("Tributo omitido", 1.4, "money"), Col("Actualizado UFV", 1.4, "money"), Col("Intereses", 1.2, "money"), Col("Sanción", 1.2, "money"), Col("Deuda tributaria", 1.5, "money")])
    for f in r["filas"]:
        t.add(f["hallazgo"], f["concepto"], f["tributo_omitido"], f["tributo_actualizado"], f["intereses"], f["sancion"], f["deuda_tributaria"])
    t.add("", "TOTAL CONTINGENCIA ESTIMADA", None, None, None, None, r["total_contingencia"], estilo="total")
    rep.notas.append("La tasa de interés y la sanción son parámetros del usuario: verifique su vigencia en la Ley 2492 y normativa del SIN.")
    return rep
