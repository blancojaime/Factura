"""Impuesto a la Propiedad de Bienes Inmuebles (Ley 843, DS 24204) – autoavalúo por zonificación y valuación zonal.

Base imponible = Valor del terreno + Valor de la construcción (+ otras construcciones)
  Terreno      = superficie × valor m² (material de vía por zona) × factor inclinación × factor servicios
  Construcción = sup. construida × valor m² (calidad) × factor depreciación (antigüedad)
Impuesto: escala (cuota fija + % sobre el excedente). Rural: alícuota fija s/ valor declarado.
"""
from decimal import Decimal

from .util import D, escala_impuesto, rnd


def _tp(db, gestion, clave, default):
    r = db.one("SELECT valor FROM tb_param WHERE gestion=? AND clave=?", (gestion, clave))
    return D(r[0]) if r else D(default)


def factor_servicios(db, gestion, inm) -> Decimal:
    minimo = _tp(db, gestion, "serv_minimo", "0.20")
    f = minimo
    for k, c in (("luz", "serv_luz"), ("agua", "serv_agua"), ("alcantarillado", "serv_alcant"), ("telefono", "serv_telef")):
        if inm[k]:
            f += _tp(db, gestion, c, "0.20")
    return min(f, Decimal(1))


def factor_inclinacion(db, gestion, inclinacion) -> Decimal:
    clave = {"PLANO": "inc_plano", "INCLINADO": "inc_inclinado", "MUY INCLINADO": "inc_muy"}.get((inclinacion or "PLANO").upper(), "inc_plano")
    d = {"inc_plano": "1.00", "inc_inclinado": "0.90", "inc_muy": "0.80"}[clave]
    return _tp(db, gestion, clave, d)


def factor_depreciacion(db, gestion, anio_construccion) -> Decimal:
    if not anio_construccion:
        return Decimal(1)
    antig = max(0, gestion - int(anio_construccion))
    r = db.one("SELECT factor FROM tb_deprec_inm WHERE gestion=? AND ? BETWEEN desde AND hasta", (gestion, antig))
    if r:
        return D(r[0])
    r = db.one("SELECT factor FROM tb_deprec_inm WHERE gestion=? ORDER BY desde DESC LIMIT 1", (gestion,))
    return D(r[0]) if r else Decimal(1)


class CalcError(Exception):
    pass


def calcular_ipbi(db, inm, gestion: int, persona="N", benemerito=False) -> dict:
    """inm: fila/dict de inmuebles. Devuelve desglose completo."""
    det = {"gestion": gestion, "tipo": inm["tipo"]}
    if (inm["exento"] or "NINGUNO") not in ("NINGUNO", "", None) and inm["exento"] != "BENEMERITO":
        det.update(base_imponible=0, impuesto=0, nota=f"Exento: {inm['exento']}")
        return det
    if inm["tipo"] == "RURAL":
        base = D(inm["valor_declarado"])
        alic = _tp(db, gestion, "ipbi_rural_alicuota", "0.20")
        imp = base * alic / 100
        det.update(base_imponible=float(rnd(base)), alicuota_rural=float(alic), impuesto=float(rnd(imp)))
        return det
    # --- terreno
    sup = D(inm["superficie"])
    if inm["tipo"] != "DEPARTAMENTO" and sup > 0:
        r = db.one("SELECT valor FROM tb_material_via WHERE gestion=? AND zona=? AND material=?", (gestion, inm["zona"], inm["material_via"]))
        if not r:
            raise CalcError(f"Falta valor de 'Material en vías' para gestión {gestion}, zona {inm['zona']}, material {inm['material_via']}.")
        vm2 = D(r[0])
        fi = factor_inclinacion(db, gestion, inm["inclinacion"])
        fs = factor_servicios(db, gestion, inm)
        v_terreno = sup * vm2 * fi * fs
        det.update(valor_m2=float(vm2), f_inclinacion=float(fi), f_servicios=float(fs))
    else:
        v_terreno = Decimal(0)
    # --- construcción
    v_const = Decimal(0)
    supc = D(inm["sup_construida"])
    if supc > 0 and inm["tipo"] in ("CASA", "DEPARTAMENTO"):
        tipo_c = "DEPARTAMENTO" if inm["tipo"] == "DEPARTAMENTO" else "CASA"
        r = db.one("SELECT valor_m2 FROM tb_calidad_const WHERE gestion=? AND tipo=? AND calidad=?", (gestion, tipo_c, inm["calidad"]))
        if not r:
            raise CalcError(f"Falta valor de construcción para gestión {gestion}, {tipo_c}, calidad {inm['calidad']}.")
        fd = factor_depreciacion(db, gestion, inm["anio_construccion"])
        v_const = supc * D(r[0]) * fd
        det.update(valor_const_m2=float(r[0]), f_depreciacion=float(fd))
    otras = D(inm["otras_construcciones"])
    base = v_terreno + v_const + otras
    tramos = [tuple(x) for x in db.all("SELECT desde,hasta,cuota_fija,porcentaje,excedente FROM tb_escala_inm WHERE gestion=? ORDER BY orden", (gestion,))]
    if not tramos:
        raise CalcError(f"No hay escala impositiva IPBI cargada para la gestión {gestion}.")
    imp = escala_impuesto(base, tramos)
    nota = ""
    if (inm["exento"] == "BENEMERITO") or benemerito:
        tope = D(tramos[0][1])                       # exención hasta el tope del primer tramo
        imp = imp - escala_impuesto(min(base, tope), tramos)
        nota = f"Benemérito: exento hasta el tope del primer tramo (Bs {tope:,.0f})"
    det.update(valor_terreno=float(rnd(v_terreno)), valor_construccion=float(rnd(v_const)), otras_construcciones=float(rnd(otras)),
               base_imponible=float(rnd(base)), impuesto=float(rnd(imp)), nota=nota)
    return det
