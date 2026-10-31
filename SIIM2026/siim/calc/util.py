from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal


def D(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x if x is not None else 0))


def rnd(x, nd=2) -> Decimal:
    q = Decimal(1).scaleb(-nd)
    return D(x).quantize(q, rounding=ROUND_HALF_UP)


def fdate(s) -> date:
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    return date.fromisoformat(str(s)[:10])


def money(x, nd=2) -> str:
    return f"{float(x):,.{nd}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def escala_impuesto(base, tramos):
    """tramos: (desde, hasta, cuota_fija, porcentaje, excedente_de). Impuesto = cuota + % × (base − excedente_de)."""
    base = D(base)
    if base <= 0 or not tramos:
        return Decimal(0)
    sel = None
    for t in sorted(tramos, key=lambda t: t[0]):
        if base >= D(t[0]):
            sel = t
    sel = sel or sorted(tramos, key=lambda t: t[0])[0]
    _, _, cuota, pct, exc = sel
    return D(cuota) + D(pct) / 100 * max(Decimal(0), base - D(exc))


def dias_habiles_despues(fecha: date, n: int, feriados=()):
    d = fecha
    c = 0
    while c < n:
        d += timedelta(days=1)
        if d.weekday() < 5 and d.isoformat() not in feriados:
            c += 1
    return d
