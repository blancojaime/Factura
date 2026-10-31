"""Impuesto a la Propiedad de Vehículos Automotores (Ley 843, DS 24205). Tablas de la Resolución anual."""
from decimal import Decimal

from .ipbi import CalcError, _tp
from .util import D, escala_impuesto, rnd

MOTOS = {"MOTOCICLETA", "MOTONETA", "TRIMOVIL", "CUADRATRACK"}
CON_CARACT = {"AUTOMOVIL", "JEEP", "VAGONETA", "CAMIONETA", "MINIBUS"}
PROCEDENCIAS = ["LATINOAMERICA", "MEXICO", "JAPON", "USA", "EUROPA_OCC", "EUROPA_OR", "COREA_ASIA"]


def codigo_cilindrada(db, gestion, cc, moto):
    r = db.one("SELECT codigo FROM tb_veh_cilindrada WHERE gestion=? AND moto=? AND ? BETWEEN desde AND hasta", (gestion, 1 if moto else 0, cc))
    if not r:
        raise CalcError(f"Falta tabla de rangos de cilindrada para gestión {gestion}.")
    return r[0]


def calcular_ipva(db, v, gestion: int, persona="N") -> dict:
    det = {"gestion": gestion, "placa": v["placa"]}
    if (v["exento"] or "NINGUNO") != "NINGUNO":
        det.update(base_imponible=0, impuesto=0, nota=f"Exento: {v['exento']}")
        return det
    tipo = (v["tipo"] or "AUTOMOVIL").upper()
    moto = tipo in MOTOS
    cod = codigo_cilindrada(db, gestion, int(v["cilindrada"] or 0), moto)
    ton = D(v["toneladas"])
    if moto:
        r = db.one("SELECT valor FROM tb_moto_valor WHERE gestion=? AND codigo=?", (gestion, cod))
        if not r:
            raise CalcError(f"Falta valor de motocicleta (gestión {gestion}, código {cod}).")
        valor = D(r[0])
    else:
        r = db.one("SELECT valor FROM tb_veh_valor WHERE gestion=? AND codigo=? AND procedencia=?", (gestion, cod, v["procedencia"]))
        if not r:
            raise CalcError(f"Falta valor (cilindrada–procedencia) gestión {gestion}, código {cod}, procedencia {v['procedencia']}.")
        valor = D(r[0])
    det.update(codigo=cod, valor_tabla=float(valor))
    if not moto:
        if ton > Decimal("1.5"):
            c = db.one("SELECT * FROM tb_veh_correccion WHERE gestion=? AND hasta_ton>=? ORDER BY tramo LIMIT 1", (gestion, float(ton)))
            if not c:
                c = db.one("SELECT * FROM tb_veh_correccion WHERE gestion=? ORDER BY tramo DESC LIMIT 1", (gestion,))
            inc = Decimal(0)
            if c:
                ch = (v["chasis"] or "").upper()
                ca = (v["carroceria"] or "").upper()
                inc += D(c["chasis_torpedo"]) if ch == "TORPEDO" else D(c["chasis_cabinado"]) if ch == "CABINADO" else 0
                inc += {"ESTACAS": D(c["carr_estacas"]), "MICRO": D(c["carr_micros"]), "BUS": D(c["carr_buses"]), "OTROS": D(c["carr_otros"])}.get(ca, 0)
            valor = valor * (1 + inc)
            det["incremento_chasis_carroceria"] = float(inc)
        elif tipo in CON_CARACT:
            adj = Decimal(1)
            if tipo != "MINIBUS" and int(v["puertas"] or 4) == 2:
                adj -= _tp(db, gestion, "veh_deduc_2puertas", "0.15")
            if v["turbo"]:
                adj += _tp(db, gestion, "veh_incr_turbo", "0.20")
            if v["doble_traccion"]:
                adj += _tp(db, gestion, "veh_incr_doble_tr", "0.15")
            valor = valor * adj
            det["ajuste_caracteristicas"] = float(adj)
    # depreciación
    anio = int(v["anio_fab"] or gestion)
    antig = max(0, gestion - anio)
    r = db.one("SELECT factor FROM tb_veh_deprec WHERE gestion=? AND antiguedad<=? ORDER BY antiguedad DESC LIMIT 1", (gestion, antig))
    fd = D(r[0]) if r else Decimal(1)
    base = valor * fd
    if persona == "J" and D(v["revalorizacion"]) > 0:
        base = D(v["revalorizacion"])
        det["nota"] = "Base = valor residual contable (revalorización técnica, persona jurídica)"
    tramos = [tuple(x) for x in db.all("SELECT desde,hasta,cuota_fija,porcentaje,excedente FROM tb_veh_escala WHERE gestion=? ORDER BY orden", (gestion,))]
    if not tramos:
        raise CalcError(f"No hay escala impositiva IPVA para la gestión {gestion}.")
    imp = escala_impuesto(base, tramos)
    det.update(f_depreciacion=float(fd), antiguedad=antig, base_imponible=float(rnd(base)), impuesto=float(rnd(imp)))
    return det
