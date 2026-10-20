"""Motor de cálculo equivalente al del VSIAF (actualización por UFV + depreciación).

Reglas (deducidas del manual del VSIAF 2.0, de los ejemplos numéricos que trae y de
las rutinas ``ffactor / vvalact / ddepgestion / ddeprecia / act_da_gestion`` del
sistema):

* ``factor``      = UFV(fecha de cálculo) / UFV(fecha de incorporación)  (6 decimales)
                    Si el grupo no se actualiza (ACTUALIZAR = .F.) el factor es 1.
                    Si el activo se deprecia y ya pasó su vida útil, la UFV final es la
                    de la fecha en que termina la vida útil (``TCVUTIL``).
* ``valor actualizado`` = costo × factor
* ``% depreciación``    = 1 / vida útil (si el grupo se deprecia)
* ``días``              = días corridos *inclusive* (11/04 → 14/10 = 187 días)
* ``dep. gestión``      = valor actualizado × % × días de la gestión / 365
* ``dep. acumulada``    = dep. acumulada inicial × factor + valor actualizado × % × días totales / 365
* ``valor neto``        = valor actualizado − dep. acumulada

Ejemplos del manual que reproduce exactamente (ver tests/test_calc.py):
  620,00 · 11/04/2013 · vida 10 · calc 14/10/2013 → 636,06 / 32,59 / 603,47
  1.380,00 · 29/08/2011 · vida 10 · calc 10/10/2013 → 1.550,03 / 120,16 / 328,69 / 1.221,34
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from .dbf import round_half_up as r2
from .ufv import UfvMissing, UfvTable

FACTOR_DECIMALS = 6
DIAS_ANIO = 365


def _is_int(x: float) -> bool:
    return abs(x - round(x)) < 1e-9


def _safe_date(y: int, m: int, d: int) -> dt.date:
    try:
        return dt.date(y, m, d)
    except ValueError:  # 29/02 en año no bisiesto
        return dt.date(y, m, 28)


def fecha_fin_vida(inc: dt.date, vida: float) -> dt.date:
    """Último día depreciable (FFECHAVUTIL del VSIAF)."""
    if _is_int(vida):
        v = int(round(vida))
        if inc.month == 2 and inc.day == 29:
            return _safe_date(inc.year + v, 2, 28)
        return _safe_date(inc.year + v, inc.month, inc.day) - dt.timedelta(days=1)
    return inc + dt.timedelta(days=int(DIAS_ANIO * vida))


def fecha_ufv_vida(inc: dt.date, vida: float) -> dt.date:
    """Fecha cuya UFV se usa como índice final al terminar la vida útil (TCVUTIL)."""
    if _is_int(vida):
        return _safe_date(inc.year + int(round(vida)), inc.month, inc.day)
    return inc + dt.timedelta(days=int(DIAS_ANIO * vida))


def dias_inclusive(desde: dt.date, hasta: dt.date) -> int:
    return max(0, (hasta - desde).days + 1)


@dataclass
class Valuation:
    costo: float
    dep_acu_inicial_input: float
    factor: float
    ufv_incorporacion: float
    ufv_calculo: float
    pct_deprecia: float          # 0..1
    dias_totales: int
    dias_gestion: int
    fin_vida: Optional[dt.date]
    valor_actualizado_ini: float  # costo actualizado al inicio de la gestión
    actualizacion_gestion: float
    valor_actualizado: float      # costo total actualizado
    dep_acumulada_ini: float
    dep_gestion: float
    actualizacion_dep: float      # actualización de la dep. acumulada en la gestión
    dep_acumulada: float
    valor_neto: float

    # --- campos "instantánea" que el VSIAF guarda en REVAL / BAJAS --------------
    @property
    def snap_depacu(self) -> float:
        """Dep. acumulada sin la depreciación de la gestión (REVAL.DEPACU / BAJAS.DEPACU)."""
        return r2(self.dep_acumulada - self.dep_gestion)

    @property
    def snap_actua(self) -> float:
        """Valor actualizado menos la dep. anterior (REVAL.ACTUA / BAJAS.ACTUA)."""
        return r2(self.valor_actualizado - self.snap_depacu)


def valuate(ufv: UfvTable, costo: float, dep_acu_inicial: float, vida: float,
            inc: dt.date, calc: dt.date, depreciar: bool = True,
            actualizar: bool = True) -> Valuation:
    """Valúa un activo a la fecha ``calc``.  Lanza ``UfvMissing`` si falta algún índice."""
    vida = float(vida or 0)
    dep_on = bool(depreciar) and vida > 0
    pct = (1.0 / vida) if dep_on else 0.0
    fin = fecha_fin_vida(inc, vida) if dep_on else None
    ufv_vida: Optional[float] = None

    def ufv_at(d: dt.date) -> float:
        nonlocal ufv_vida
        if dep_on and fin is not None and d > fin:
            if ufv_vida is None:
                ufv_vida = ufv.get(fecha_ufv_vida(inc, vida))
            return ufv_vida
        return ufv.get(d)

    def factor_at(d: dt.date) -> float:
        if not actualizar:
            return 1.0
        return round(ufv_at(d) / ufv_inc, FACTOR_DECIMALS)

    ufv_inc = ufv.get(inc)
    if calc < inc:
        return Valuation(costo, dep_acu_inicial, 1.0, ufv_inc, ufv_inc, pct, 0, 0, fin,
                         costo, 0.0, costo, dep_acu_inicial, 0.0, 0.0, dep_acu_inicial,
                         r2(costo - dep_acu_inicial))

    factor = factor_at(calc)
    valact = r2(costo * factor)
    end = min(calc, fin) if fin else calc
    d_tot = dias_inclusive(inc, end) if dep_on else 0
    d_ges = dias_inclusive(max(inc, dt.date(calc.year, 1, 1)), end) if dep_on else 0
    dep_ges = r2(valact * pct * d_ges / DIAS_ANIO)
    dep_acu = r2(dep_acu_inicial * factor) + r2(valact * pct * d_tot / DIAS_ANIO)
    dep_acu = min(dep_acu, valact) if valact > 0 else dep_acu

    # Situación al inicio de la gestión
    if inc.year < calc.year:
        prev_end = dt.date(calc.year - 1, 12, 31)
        f_prev = factor_at(prev_end)
        valact_ini = r2(costo * f_prev)
        end_prev = min(prev_end, fin) if fin else prev_end
        d_prev = dias_inclusive(inc, end_prev) if dep_on else 0
        dep_ini = r2(dep_acu_inicial * f_prev) + r2(valact_ini * pct * d_prev / DIAS_ANIO)
        dep_ini = min(dep_ini, valact_ini) if valact_ini > 0 else dep_ini
    else:
        valact_ini = costo
        dep_ini = dep_acu_inicial

    return Valuation(
        costo=costo, dep_acu_inicial_input=dep_acu_inicial, factor=factor,
        ufv_incorporacion=ufv_inc, ufv_calculo=ufv_at(calc), pct_deprecia=pct,
        dias_totales=d_tot, dias_gestion=d_ges, fin_vida=fin,
        valor_actualizado_ini=valact_ini,
        actualizacion_gestion=r2(valact - valact_ini),
        valor_actualizado=valact,
        dep_acumulada_ini=dep_ini, dep_gestion=dep_ges,
        actualizacion_dep=r2(dep_acu - dep_ini - dep_ges),
        dep_acumulada=dep_acu, valor_neto=r2(valact - dep_acu),
    )


__all__ = ["valuate", "Valuation", "fecha_fin_vida", "fecha_ufv_vida", "UfvMissing"]
