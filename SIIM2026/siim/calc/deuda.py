"""Cálculo de la Deuda Tributaria (Ley 2492, DS 27310). Fórmulas de los "Apuntes Tributarios SIIM".

DT = TO × (1 + r/360)^n + M       (expresada en UFV, convertida a Bs con la UFV de la fecha de pago)

* Deudas posteriores al 26/12/2002 (vigencia UFV):   Mv = (UFVfp/UFVfv − 1) × TO
* Deudas anteriores al 26/12/2002: se actualiza con el tipo de cambio del dólar:
      Mv = ((TCus26/TCusFV) × (UFVfp/UFV26) − 1) × OTfv ;  TO26 = OTfv × TCus26/TCusFV
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .util import D, fdate, rnd

CORTE_UFV = date(2002, 12, 26)


@dataclass
class DeudaParams:
    r: Decimal                       # tasa anual de interés activa UFV + 3 puntos (ej. 0.1082)
    persona: str = "N"               # N natural | J jurídica
    multa_df: bool = True            # aplica multa por incumplimiento de deberes formales (DJ fuera de plazo)
    df_pct: Decimal = Decimal("0.10")
    df_min_n: Decimal = Decimal(50)
    df_min_j: Decimal = Decimal(240)
    df_max: Decimal = Decimal(2400)
    modo_df_ufv: str = "DIVISION"    # DIVISION (TO/UFV, definición legal) | SIIM_PDF (TO×UFV, como aparece en los apuntes)
    decimales: int = 0               # redondeo de componentes (0 = bolivianos enteros)
    sancion_adm: Decimal = Decimal(0)  # sanción administrativa fija en Bs (opcional)


@dataclass
class Deuda:
    to_bs: Decimal
    fv: date
    fp: date
    mora: int
    mv: Decimal
    to_mv: Decimal
    interes: Decimal
    multa_ufv: Decimal
    multa_bs: Decimal
    sancion: Decimal
    total: Decimal
    anterior_2002: bool
    to_ufv_df: Decimal = Decimal(0)
    detalle: dict = field(default_factory=dict)

    def as_dict(self):
        d = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in self.__dict__.items() if k != "detalle"}
        d["fv"], d["fp"] = self.fv.isoformat(), self.fp.isoformat()
        d["detalle"] = self.detalle
        return d


def dias_mora(fv: date, fp: date) -> int:
    """Desde el día siguiente al vencimiento hasta el día de pago inclusive."""
    return max(0, (fp - fv).days)


def multa_deberes_formales(to_ufv_base: Decimal, ufv_fp: Decimal, p: DeudaParams):
    """MUFV = 10% del TO en UFV, acotada entre mínimo (50 N / 240 J) y 2.400 UFV; MBs = MUFV × UFVfp."""
    m = to_ufv_base * p.df_pct
    mn = p.df_min_j if p.persona == "J" else p.df_min_n
    m = min(max(m, mn), p.df_max)
    return m, m * ufv_fp


def calcular_deuda(to_bs, fv, fp, ufv_fv, ufv_fp, p: DeudaParams, usd_fv=None, usd_26=None, ufv_26=None) -> Deuda:
    to_bs, ufv_fv, ufv_fp = D(to_bs), D(ufv_fv), D(ufv_fp)
    fv, fp = fdate(fv), fdate(fp)
    n = dias_mora(fv, fp)
    nd = p.decimales
    anterior = fv < CORTE_UFV
    base_r = (Decimal(1) + D(p.r) / 360)
    factor = base_r ** n if n else Decimal(1)
    if n == 0:
        z = Decimal(0)
        return Deuda(to_bs, fv, fp, 0, z, rnd(to_bs, nd), z, z, z, z, rnd(to_bs, nd), anterior)
    if anterior:
        if not (usd_fv and usd_26 and ufv_26):
            raise ValueError("Deuda anterior al 26/12/2002: se requiere dólar del vencimiento, dólar y UFV del 26/12/2002.")
        usd_fv, usd_26, ufv_26 = D(usd_fv), D(usd_26), D(ufv_26)
        mv = ((usd_26 / usd_fv) * (ufv_fp / ufv_26) - 1) * to_bs
        to26 = to_bs * usd_26 / usd_fv
        to_mv = to_bs + mv
        interes = (to26 / ufv_26) * factor * ufv_fp - to_mv
        base_df = to26 * ufv_26 if p.modo_df_ufv == "SIIM_PDF" else to26 / ufv_26
        det = dict(TO26=float(rnd(to26, 4)))
    else:
        mv = (ufv_fp / ufv_fv - 1) * to_bs
        to_mv = to_bs + mv
        interes = (to_bs / ufv_fv) * factor * ufv_fp - to_mv
        base_df = to_bs * ufv_fv if p.modo_df_ufv == "SIIM_PDF" else to_bs / ufv_fv
        det = {}
    mv, to_mv, interes = rnd(mv, nd), rnd(to_bs, nd) + rnd(mv, nd), rnd(interes, nd)
    mufv, mbs = (Decimal(0), Decimal(0))
    if p.multa_df:
        mufv, mbs = multa_deberes_formales(base_df, ufv_fp, p)
        mufv, mbs = rnd(mufv, nd), rnd(mbs, nd)
    sanc = rnd(p.sancion_adm, nd)
    total = to_mv + interes + mbs + sanc
    det.update(factor_interes=float(rnd(factor, 6)), r=float(p.r))
    return Deuda(rnd(to_bs, nd), fv, fp, n, mv, to_mv, interes, mufv, mbs, sanc, total, anterior, rnd(base_df, 3), det)
