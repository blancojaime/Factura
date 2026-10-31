"""Plan de pagos (facilidades – Art. 55 Ley 2492): cuotas mensuales iguales (sistema francés)."""
from datetime import date

from .util import D, fdate, rnd


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    import calendar
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def generar_plan(deuda, cuota_inicial, n_cuotas, tasa_anual, fecha, tasa_en_dias=False):
    deuda, ci = D(deuda), D(cuota_inicial)
    cap = deuda - ci
    if cap <= 0 or n_cuotas < 1:
        raise ValueError("Deuda a financiar y número de cuotas deben ser positivos.")
    i = D(tasa_anual) / 12
    cuota = cap / n_cuotas if i == 0 else cap * i / (1 - (1 + i) ** (-n_cuotas))
    cuota = rnd(cuota)
    saldo = cap
    rows = []
    f0 = fdate(fecha)
    for k in range(1, n_cuotas + 1):
        inte = rnd(saldo * i)
        capital = cuota - inte if k < n_cuotas else saldo
        monto = capital + inte if k == n_cuotas else cuota
        saldo = rnd(saldo - capital)
        rows.append(dict(nro=k, vence=_add_months(f0, k).isoformat(), capital=float(rnd(capital)), interes=float(inte), monto=float(rnd(monto)), saldo=float(saldo)))
    return rows
