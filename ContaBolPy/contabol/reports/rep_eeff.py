"""Estados financieros: balance general, resultados, evolución del patrimonio, flujo de efectivo (directo e indirecto), notas y paquete completo."""
from __future__ import annotations

from ..util import fdate, to_date
from .catalogo import MOD_EEFF, P_BOOL, P_DESDE, P_FECHA, P_HASTA, P_MONEDA, P_NIVEL, ParamDef, reporte
from .engine import Col, ReporteDef, base

FIRMAS = ["Contador", "Representante Legal"]


def _tabla_estado(rep: ReporteDef, est: dict, titulo: str = "", con_codigo: bool = False):
    cols = [Col("Concepto", 6), Col("Importe", 1.7, "money")]
    t = rep.tabla(cols, titulo=titulo)
    for f in est["filas"]:
        t.add(f["texto"], f["importe"], estilo=f.get("estilo", ""), nivel=f.get("nivel", 0))
    return t


def _bg(ctx, p, rep: ReporteDef | None = None, solo=True):
    est = ctx.estados.balance_general(p["fecha"], int(p["nivel"]), p["moneda"])
    rep = rep or base(ctx, "Balance General", f"Al {fdate(p['fecha'])}", moneda=p["moneda"])
    _tabla_estado(rep, est)
    if not est["cuadra"]:
        rep.notas.append(f"ATENCIÓN: el balance presenta una diferencia de {est['diferencia']:,.2f}. Revise los comprobantes.")
    return rep


@reporte("balance_general", "Balance General", MOD_EEFF, "CONT.REPORTES", [P_FECHA("Al"), P_NIVEL(), P_MONEDA()], "Estado de situación patrimonial a una fecha.")
def balance_general(ctx, p):
    return _bg(ctx, p)


def _er(ctx, p, rep=None):
    est = ctx.estados.estado_resultados(p["desde"], p["hasta"], int(p["nivel"]), p["moneda"])
    rep = rep or base(ctx, "Estado de Resultados", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}", moneda=p["moneda"])
    _tabla_estado(rep, est)
    return rep


@reporte("estado_resultados", "Estado de Resultados", MOD_EEFF, "CONT.REPORTES", [P_DESDE(), P_HASTA(), P_NIVEL(), P_MONEDA()])
def estado_resultados(ctx, p):
    return _er(ctx, p)


def _ep(ctx, p, rep=None):
    est = ctx.estados.evolucion_patrimonio(p["desde"], p["hasta"])
    rep = rep or base(ctx, "Estado de Evolución del Patrimonio Neto", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}", horizontal=True)
    cols = [Col("Concepto", 5)] + [Col(n, 1.7, "money") for _, n in est["columnas"]] + [Col("Total", 1.8, "money")]
    t = rep.tabla(cols)
    for f in est["filas"]:
        vals = [f["valores"].get(k) for k, _ in est["columnas"]]
        t.add(f["texto"], *vals, round(sum(v or 0 for v in vals), 2), estilo=f["estilo"])
    return rep


@reporte("evolucion_patrimonio", "Estado de Evolución del Patrimonio Neto", MOD_EEFF, "CONT.REPORTES", [P_DESDE(), P_HASTA()])
def evolucion_patrimonio(ctx, p):
    return _ep(ctx, p)


def _fd(ctx, p, rep=None):
    est = ctx.estados.flujo_directo(p["desde"], p["hasta"])
    rep = rep or base(ctx, "Estado de Flujo de Efectivo - Método Directo", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}")
    _tabla_estado(rep, est)
    return rep


def _fi(ctx, p, rep=None):
    est = ctx.estados.flujo_indirecto(p["desde"], p["hasta"])
    rep = rep or base(ctx, "Estado de Flujo de Efectivo - Método Indirecto", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}")
    _tabla_estado(rep, est)
    return rep


@reporte("flujo_directo", "Flujo de Efectivo - Método Directo", MOD_EEFF, "CONT.REPORTES", [P_DESDE(), P_HASTA()])
def flujo_directo(ctx, p):
    return _fd(ctx, p)


@reporte("flujo_indirecto", "Flujo de Efectivo - Método Indirecto", MOD_EEFF, "CONT.REPORTES", [P_DESDE(), P_HASTA()])
def flujo_indirecto(ctx, p):
    return _fi(ctx, p)


def _notas(ctx, p, rep=None):
    rep = rep or base(ctx, "Notas a los Estados Financieros", f"Del {fdate(p['desde'])} al {fdate(p['hasta'])}")
    for n in ctx.estados.notas(p["desde"], p["hasta"]):
        rep.texto(f"NOTA {n['n']} - {n['titulo']}", "titulo")
        for par in n["parrafos"]:
            rep.texto(par)
        tb = n.get("tabla")
        if tb and tb["filas"]:
            cols = [Col(c, 3 if c in ("Cuenta", "Grupo") else 1.4, "txt" if c in ("Código", "Cuenta", "Grupo") else "money") for c in tb["cols"]]
            t = rep.tabla(cols)
            for f in tb["filas"]:
                t.add(*f, estilo="total" if "TOTAL" in f[:2] else "")
    return rep


@reporte("notas_eeff", "Notas a los Estados Financieros", MOD_EEFF, "CONT.REPORTES", [P_DESDE(), P_HASTA()])
def notas_eeff(ctx, p):
    return _notas(ctx, p)


@reporte("estados_financieros", "Estados Financieros completos (los 6 estados)", MOD_EEFF, "CONT.REPORTES",
         [P_DESDE(), P_HASTA(), P_NIVEL()], "Balance, Resultados, Evolución del Patrimonio, Flujo directo, Flujo indirecto y Notas en un solo documento.")
def estados_completos(ctx, p):
    rep = base(ctx, "Estados Financieros", f"Gestión del {fdate(p['desde'])} al {fdate(p['hasta'])}", horizontal=False)
    rep.texto("1. BALANCE GENERAL", "titulo")
    _bg(ctx, {"fecha": p["hasta"], "nivel": p["nivel"], "moneda": "BS"}, rep)
    rep.texto("", "salto")
    rep.texto("2. ESTADO DE RESULTADOS", "titulo")
    _er(ctx, {"desde": p["desde"], "hasta": p["hasta"], "nivel": p["nivel"], "moneda": "BS"}, rep)
    rep.texto("", "salto")
    rep.texto("3. ESTADO DE EVOLUCIÓN DEL PATRIMONIO NETO", "titulo")
    est = ctx.estados.evolucion_patrimonio(p["desde"], p["hasta"])
    cols = [Col("Concepto", 5)] + [Col(n, 1.6, "money") for _, n in est["columnas"]] + [Col("Total", 1.7, "money")]
    t = rep.tabla(cols)
    for f in est["filas"]:
        vals = [f["valores"].get(k) for k, _ in est["columnas"]]
        t.add(f["texto"], *vals, round(sum(v or 0 for v in vals), 2), estilo=f["estilo"])
    rep.texto("", "salto")
    rep.texto("4. ESTADO DE FLUJO DE EFECTIVO - MÉTODO DIRECTO", "titulo")
    _fd(ctx, p, rep)
    rep.texto("", "salto")
    rep.texto("5. ESTADO DE FLUJO DE EFECTIVO - MÉTODO INDIRECTO", "titulo")
    _fi(ctx, p, rep)
    rep.texto("", "salto")
    rep.texto("6. NOTAS A LOS ESTADOS FINANCIEROS", "titulo")
    _notas(ctx, p, rep)
    return rep
