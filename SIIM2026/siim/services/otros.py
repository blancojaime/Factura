"""Otros ingresos: Formulario Único de Caja (FUC), estructura de rubros/subniveles, contratos y devengados."""
from datetime import date

from ..calc.util import D, rnd
from .base import Ctx, ServiceError, ahora, hoy, numero


def costo_item(sub, base=None):
    if D(sub["monto"]) > 0:
        return float(sub["monto"])
    if D(sub["porcentaje"]) > 0:
        if base is None:
            raise ServiceError(f"'{sub['descripcion']}' se calcula como {sub['porcentaje']}% de una base: indique el valor base.")
        return float(rnd(D(base) * D(sub["porcentaje"]) / 100))
    raise ServiceError(f"El subnivel '{sub['descripcion']}' no tiene monto ni porcentaje definidos.")


def crear_fuc(ctx: Ctx, nombre: str, items, documento="", detalle="", contrato_id=None, fecha=None) -> int:
    """items: [{'subnivel': codigo, 'cantidad': n, 'base': opcional}]. Queda en BORRADOR hasta recaudar."""
    ctx.require("otros.fuc")
    if not nombre.strip():
        raise ServiceError("Indique el nombre del contribuyente/beneficiario.")
    if not items:
        raise ServiceError("Agregue al menos un concepto.")
    db = ctx.db
    with db.tx():
        total = 0.0
        det = []
        for it in items:
            s = db.one("SELECT * FROM subniveles WHERE codigo=? AND activo=1", (it["subnivel"],))
            if not s or s["tipo"] == "AGREGACION":
                raise ServiceError(f"Subnivel {it['subnivel']} inválido (sólo subniveles de entrada).")
            cant = float(it.get("cantidad", 1))
            if cant <= 0:
                raise ServiceError("La cantidad debe ser mayor a cero.")
            costo = costo_item(s, it.get("base"))
            t = float(rnd(D(costo) * D(cant)))
            total += t
            det.append((s["rubro"], s["codigo"], s["descripcion"], costo, cant, t))
        fid = db.insert("fuc", dict(nro=numero(db, "FUC", fecha), fecha=fecha or hoy(), hora=ahora(), nombre=nombre.strip(), documento=documento, detalle=detalle,
                                    estado="BORRADOR", total=float(rnd(D(total))), contrato_id=contrato_id, usuario=ctx.user))
        for d in det:
            db.insert("fuc_det", dict(fuc_id=fid, rubro=d[0], subnivel=d[1], descripcion=d[2], costo=d[3], cantidad=d[4], total=d[5]))
        ctx.log("FUC_CREADO", "fuc", fid, {"total": total})
    return fid


def recaudar_fuc(ctx: Ctx, fid: int, fecha=None, modalidad="CAJA", entidad=""):
    ctx.require("otros.fuc")
    f = ctx.db.one("SELECT * FROM fuc WHERE id=?", (fid,))
    if not f or f["estado"] != "BORRADOR":
        raise ServiceError("Sólo se recauda un FUC en estado BORRADOR.")
    ctx.db.update("fuc", dict(estado="RECAUDADO", fecha_pago=fecha or hoy(), cajero=ctx.user, modalidad=modalidad, entidad=entidad), "id=?", (fid,))
    ctx.log("FUC_RECAUDADO", "fuc", fid, {"total": f["total"]})


def anular_fuc(ctx: Ctx, fid: int, motivo: str):
    ctx.require("otros.anular")
    f = ctx.db.one("SELECT * FROM fuc WHERE id=?", (fid,))
    if not f or f["estado"] != "RECAUDADO":
        raise ServiceError("Sólo puede anularse un FUC RECAUDADO (los borradores se borran).")
    if not motivo.strip():
        raise ServiceError("Indique el motivo.")
    ctx.db.update("fuc", dict(estado="ANULADO", anulado_motivo=motivo), "id=?", (fid,))
    ctx.log("FUC_ANULADO", "fuc", fid, {"motivo": motivo})


def borrar_fuc(ctx: Ctx, fid: int):
    ctx.require("otros.fuc")
    f = ctx.db.one("SELECT * FROM fuc WHERE id=?", (fid,))
    if not f or f["estado"] != "BORRADOR":
        raise ServiceError("Sólo pueden borrarse FUC en BORRADOR.")
    with ctx.db.tx():
        ctx.db.execute("DELETE FROM fuc_det WHERE fuc_id=?", (fid,))
        ctx.db.execute("DELETE FROM fuc WHERE id=?", (fid,))
        ctx.log("FUC_BORRADO", "fuc", fid)


# ---- contratos (alquileres, concesiones) y devengados
def crear_contrato(ctx: Ctx, subnivel: str, beneficiario: str, monto: float, inicio: str, fin=None, documento="", frecuencia="MENSUAL") -> int:
    ctx.require("otros.fuc")
    if not ctx.db.one("SELECT 1 FROM subniveles WHERE codigo=?", (subnivel,)):
        raise ServiceError("Subnivel inexistente.")
    cid = ctx.db.insert("contratos", dict(nro=numero(ctx.db, "CTR"), fecha=hoy(), subnivel=subnivel, beneficiario=beneficiario, documento=documento, monto_periodico=monto,
                                           frecuencia=frecuencia, inicio=inicio, fin=fin, usuario=ctx.user))
    ctx.log("CONTRATO", "contratos", cid)
    return cid


def periodos_transcurridos(inicio, fin, frecuencia, hasta) -> int:
    a = date.fromisoformat(inicio)
    b = date.fromisoformat(min(hasta, fin) if fin else hasta)
    if b < a:
        return 0
    meses = (b.year - a.year) * 12 + b.month - a.month + 1
    paso = {"MENSUAL": 1, "TRIMESTRAL": 3, "SEMESTRAL": 6, "ANUAL": 12}.get(frecuencia, 1)
    return -(-meses // paso)


def devengados(db, hasta=None):
    hasta = hasta or hoy()
    out = []
    for c in db.all("SELECT * FROM contratos WHERE estado='VIGENTE' ORDER BY nro"):
        n = periodos_transcurridos(c["inicio"], c["fin"], c["frecuencia"], hasta)
        dev = n * c["monto_periodico"]
        perc = db.scalar("SELECT COALESCE(SUM(total),0) FROM fuc WHERE contrato_id=? AND estado='RECAUDADO'", (c["id"],), 0)
        out.append(dict(nro=c["nro"], fecha=c["fecha"], subnivel=c["subnivel"], beneficiario=c["beneficiario"], periodos=n, devengado=dev, percibido=perc, saldo=dev - perc))
    return out
