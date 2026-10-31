"""Patente de Funcionamiento (actividades económicas) – múltiples modalidades de cálculo.

Modalidades (parámetro 'patente_modalidad'):
  TOPE_ZONA_SUP : PF = PMA × PZS/100  (Patente Máxima Anual × % zona-superficie)      [Ordenanza modelo, Guía SIIM]
  PUA           : PF = superficie × valor m² de la zona (Patente Única Anual), limitada por el tope si existe
  CATEGORIA     : PF = monto fijo por actividad/categoría
Ajustes opcionales (mejoras): factor de consumo eléctrico, actualización por variación del dólar (art. 22 ordenanza modelo),
proporcional por duodécimas (inicio/cese en la gestión), mínimo, exención.
"""
from datetime import date
from decimal import Decimal

from .ipbi import CalcError
from .util import D, fdate, rnd

MODALIDADES = {"TOPE_ZONA_SUP": "Patente máxima × % zona-superficie", "PUA": "Patente Única Anual (valor por m²)", "CATEGORIA": "Monto fijo por categoría"}


def meses_en_gestion(inicio, cese, gestion: int) -> int:
    """Duodécimas: meses (completos, contando el mes de inicio y el de cese) que la actividad funcionó en la gestión."""
    a, b = 1, 12
    if inicio:
        i = fdate(inicio)
        if i.year > gestion:
            return 0
        if i.year == gestion:
            a = i.month
    if cese:
        c = fdate(cese)
        if c.year < gestion:
            return 0
        if c.year == gestion:
            b = c.month
    return max(0, b - a + 1)


def porcentaje_zona_superficie(db, gestion, zona, sup):
    r = db.one("SELECT porcentaje FROM tb_act_zona_sup WHERE gestion=? AND zona=? AND ?>=desde AND ?<=hasta ORDER BY desde LIMIT 1", (gestion, zona, float(sup), float(sup)))
    if not r:
        r = db.one("SELECT porcentaje FROM tb_act_zona_sup WHERE gestion=? AND zona=? ORDER BY desde DESC LIMIT 1", (gestion, zona))
    if not r:
        raise CalcError(f"Falta la tabla Zona–Superficie–Porcentaje (gestión {gestion}, zona {zona}).")
    return D(r[0])


def calcular_paf(db, act, gestion: int, modalidad=None) -> dict:
    modalidad = modalidad or db.param("patente_modalidad", "TOPE_ZONA_SUP")
    det = {"gestion": gestion, "modalidad": modalidad}
    if (act["exento"] or "NINGUNO") != "NINGUNO":
        det.update(base_imponible=0, impuesto=0, nota=f"Exento: {act['exento']} (debe presentar DJ)")
        return det
    meses = meses_en_gestion(act["fecha_inicio"], act["fecha_cese"], gestion)
    if meses == 0:
        det.update(base_imponible=0, impuesto=0, nota="La actividad no funcionó en la gestión")
        return det
    tope = db.one("SELECT tope,fijo FROM tb_act_tope WHERE gestion=? AND act=? AND cat=?", (gestion, act["act"], act["cat"]))
    sup = D(act["superficie"])
    if modalidad == "TOPE_ZONA_SUP":
        if not tope or not D(tope["tope"]):
            raise CalcError(f"Falta la Patente Máxima Anual para actividad {act['act']}-{act['cat']} (gestión {gestion}).")
        pzs = porcentaje_zona_superficie(db, gestion, act["zona"], sup)
        pf = D(tope["tope"]) * pzs / 100
        det.update(patente_maxima=float(tope["tope"]), pzs=float(pzs))
    elif modalidad == "PUA":
        r = db.one("SELECT valor_m2 FROM tb_act_pua WHERE gestion=? AND zona=?", (gestion, act["zona"]))
        if not r:
            raise CalcError(f"Falta el valor por m² (PUA) para la zona {act['zona']}, gestión {gestion}.")
        pf = sup * D(r[0])
        if tope and D(tope["tope"]) > 0:
            pf = min(pf, D(tope["tope"]))
        det.update(valor_m2=float(r[0]), superficie=float(sup))
    elif modalidad == "CATEGORIA":
        if not tope or not D(tope["fijo"]):
            raise CalcError(f"Falta el monto fijo de la categoría {act['act']}-{act['cat']} (gestión {gestion}).")
        pf = D(tope["fijo"])
    else:
        raise CalcError(f"Modalidad desconocida: {modalidad}")
    # factor de consumo eléctrico (opcional, si hay tabla)
    kwh = D(act["consumo_elect"])
    if kwh > 0:
        r = db.one("SELECT factor FROM tb_act_consumo WHERE gestion=? AND ?>=desde AND ?<=hasta LIMIT 1", (gestion, float(kwh), float(kwh)))
        if r:
            pf = pf * D(r[0])
            det["f_consumo"] = float(r[0])
    # actualización por variación del dólar (1/ene → 31/dic)
    if db.param("patente_actualiza_dolar", "0") == "1":
        a = db.one("SELECT dolar FROM cotizaciones WHERE fecha>=? ORDER BY fecha LIMIT 1", (f"{gestion}-01-01",))
        b = db.one("SELECT dolar FROM cotizaciones WHERE fecha<=? ORDER BY fecha DESC LIMIT 1", (f"{gestion}-12-31",))
        if a and b and D(a[0]) > 0:
            f = D(b[0]) / D(a[0])
            if f > 1:
                pf *= f
                det["f_actualizacion_dolar"] = float(rnd(f, 6))
    if meses < 12:
        pf = pf * meses / 12
        det["duodecimas"] = f"{meses}/12"
    minimo = D(db.param("patente_minima", "0"))
    if minimo and pf < minimo:
        pf = minimo
        det["nota"] = f"Se aplicó patente mínima Bs {minimo}"
    det.update(base_imponible=float(rnd(pf)), impuesto=float(rnd(pf)))
    return det


def calcular_publicidad(db, pub, gestion: int) -> dict:
    if (pub["exento"] or "NINGUNO") != "NINGUNO":
        return dict(base_imponible=0, impuesto=0, nota=f"Exento: {pub['exento']}")
    r = db.one("SELECT valor_m2 FROM tb_publicidad WHERE gestion=? AND tipo=?", (gestion, pub["tipo"]))
    if not r:
        raise CalcError(f"Falta el arancel de publicidad '{pub['tipo']}' para la gestión {gestion}.")
    area = D(pub["ancho"]) * D(pub["alto"])
    imp = area * D(r[0])
    return dict(area_m2=float(rnd(area)), valor_m2=float(r[0]), base_imponible=float(rnd(imp)), impuesto=float(rnd(imp)))
