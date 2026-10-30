"""Catálogo de informes parametrizados: cada uno se ve en pantalla, se imprime y se exporta a PDF y Excel."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from ..sistema import ErrorNegocio
from .engine import ReporteDef


@dataclass
class ParamDef:
    clave: str
    titulo: str
    tipo: str   # desde, hasta, fecha, mes, nivel, moneda, cuenta, tercero_c, tercero_p, tercero, item, empleado, almacen, bool, texto, lista, entero, orden, comprobante, tipo_comp
    defecto: Callable | object = None
    opciones: list[tuple[str, str]] | None = None
    requerido: bool = False


@dataclass
class ReporteCat:
    id: str
    titulo: str
    modulo: str
    permiso: str
    construir: Callable
    params: list[ParamDef] = field(default_factory=list)
    descripcion: str = ""


MOD_CONT, MOD_EEFF, MOD_IVA, MOD_COM, MOD_INV, MOD_AF, MOD_RH, MOD_COS, MOD_ADM = (
    "Contabilidad", "Estados financieros", "Impuestos (IVA e IT)", "Comercial", "Inventarios", "Activos fijos", "Planillas y RR.HH.", "Costos y producción", "Administración")

_REGISTRO: list[ReporteCat] = []


def reporte(id: str, titulo: str, modulo: str, permiso: str, params: list[ParamDef] | None = None, descripcion: str = ""):
    def deco(fn):
        _REGISTRO.append(ReporteCat(id, titulo, modulo, permiso, fn, params or [], descripcion))
        return fn
    return deco


# ---- parámetros frecuentes
def P_DESDE(): return ParamDef("desde", "Desde", "desde", lambda c: c.inicio)
def P_HASTA(): return ParamDef("hasta", "Hasta", "hasta", lambda c: c.fin)
def P_FECHA(t="Al"): return ParamDef("fecha", t, "fecha", lambda c: c.fin)
def P_NIVEL(): return ParamDef("nivel", "Hasta nivel de cuenta", "nivel", 5)
def P_MONEDA(): return ParamDef("moneda", "Moneda", "moneda", "BS")
def P_MES(): return ParamDef("mes", "Mes", "mes", lambda c: min(max(date.today().month, 1), 12) if c.inicio.year == date.today().year else 12)
def P_BOOL(clave, titulo, defecto=False): return ParamDef(clave, titulo, "bool", defecto)


def todos() -> list[ReporteCat]:
    _cargar()
    return list(_REGISTRO)


def buscar(id: str) -> ReporteCat:
    _cargar()
    for r in _REGISTRO:
        if r.id == id:
            return r
    raise KeyError(id)


def valores_defecto(ctx, rep: ReporteCat) -> dict:
    v = {}
    for p in rep.params:
        d = p.defecto(ctx) if callable(p.defecto) else p.defecto
        v[p.clave] = d
    return v


def ejecutar(ctx, id: str, valores: dict | None = None) -> ReporteDef:
    rep = buscar(id)
    ctx.requiere(rep.permiso)
    v = valores_defecto(ctx, rep)
    v.update({k: x for k, x in (valores or {}).items() if x is not None})
    for p in rep.params:
        if p.requerido and not v.get(p.clave):
            raise ErrorNegocio(f"Falta el parámetro: {p.titulo}.")
    r = rep.construir(ctx, v)
    r.nombre_archivo = rep.id
    return r


_cargado = False


def _cargar():
    global _cargado
    if _cargado:
        return
    _cargado = True
    from . import rep_contables, rep_eeff, rep_iva, rep_comercial, rep_inventario, rep_rrhh, rep_otros  # noqa: F401
