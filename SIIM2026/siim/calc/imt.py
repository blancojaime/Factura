"""Impuesto Municipal a las Transferencias (Ley 1606, DS 24054): 3% sobre el mayor entre el valor pagado y la base del IPBI/IPVA de la última gestión vencida."""
from datetime import date

from .util import D, dias_habiles_despues, fdate, rnd


def calcular_imt(db, monto_bs, base_ultima_gestion, fecha_hecho, alicuota=None):
    alic = D(alicuota if alicuota is not None else db.param_f("imt_alicuota", 3.0))
    base = max(D(monto_bs), D(base_ultima_gestion))
    imp = base * alic / 100
    fer = {r[0] for r in db.all("SELECT fecha FROM cotizaciones WHERE tipo_dia='FERIADO'")}
    limite = dias_habiles_despues(fdate(fecha_hecho), 10, fer)
    return dict(base_imponible=float(rnd(base)), alicuota=float(alic), impuesto=float(rnd(imp)), fecha_limite=limite.isoformat(),
                monto_declarado=float(rnd(D(monto_bs))), base_gestion=float(rnd(D(base_ultima_gestion))))
