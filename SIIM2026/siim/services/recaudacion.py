"""Recaudación: cobro, anulación, transferencia de dominio (IMT), cuenta corriente, plan de pagos y conciliación bancaria."""
from datetime import date
from decimal import Decimal

from ..calc.plan import generar_plan
from ..calc.util import D, rnd
from .base import Ctx, ServiceError, ahora, hoy, j, numero, row_dict
from .liquidacion import TABLA, deuda_a_fecha, preliquidar


def _check_fecha(ctx, fecha):
    if fecha and fecha != hoy() and ctx.session is not None and not ctx.session.can("rec.anular"):
        raise ServiceError("Sólo un supervisor puede registrar pagos con fecha distinta a la de hoy.")
    if fecha and fecha > hoy():
        raise ServiceError("La fecha de pago no puede ser futura.")


def cobrar(ctx: Ctx, liq_id: int, fecha=None, modalidad="CAJA", entidad="", cuota_id=None, importe_recibido=None) -> int:
    ctx.require("rec.cobrar")
    db = ctx.db
    fecha = fecha or hoy()
    _check_fecha(ctx, fecha)
    with db.tx():
        liq = db.one("SELECT * FROM liquidaciones WHERE id=?", (liq_id,))
        if not liq:
            raise ServiceError("Liquidación no encontrada.")
        if liq["estado"] not in ("PENDIENTE", "PARCIAL"):
            raise ServiceError(f"La liquidación {liq['nro']} está {liq['estado']}; no puede cobrarse.")
        d = deuda_a_fecha(db, liq, fecha, cuota_id)
        if importe_recibido is not None and abs(float(importe_recibido) - d["total"]) > 0.005:
            raise ServiceError(f"El importe recibido ({importe_recibido:,.2f}) no coincide con el total a pagar ({d['total']:,.2f}).")
        recibo = numero(db, "REC")
        pid = db.insert("pagos", dict(nro_recibo=recibo, liq_id=liq_id, cuota_id=cuota_id, rubro=liq["rubro"], pmc=liq["pmc"], gestion=liq["gestion"], fecha=fecha, hora=ahora(),
                                      modalidad=modalidad, cajero=ctx.user, entidad=entidad, monto_neto=d["neto"], descuento=d["descuento"], mant_valor=d["mant_valor"],
                                      interes=d["interes"], multa_df=d["multa_df"], sancion=d["sancion"], total=d["total"], detalle=j(d), usuario=ctx.user))
        if cuota_id:
            db.update("liq_cuotas", {"estado": "PAGADA"}, "id=?", (cuota_id,))
            pend = db.scalar("SELECT COUNT(*) FROM liq_cuotas WHERE liq_id=? AND estado='PENDIENTE'", (liq_id,), 0)
            db.update("liquidaciones", {"estado": "PAGADA" if not pend else "PARCIAL"}, "id=?", (liq_id,))
        else:
            db.update("liquidaciones", {"estado": "PAGADA"}, "id=?", (liq_id,))
        if liq["rubro"] == "IMT":
            _aplicar_transferencia(ctx, liq)
        ctx.log("PAGO", "pagos", pid, {"recibo": recibo, "total": d["total"], "liq": liq["nro"]})
    return pid


def _aplicar_transferencia(ctx, liq):
    t = ctx.db.one("SELECT * FROM transferencias WHERE id=?", (liq["objeto_id"],))
    tabla = "inmuebles" if t["tipo"] == "INM" else "vehiculos"
    ctx.db.update(tabla, {"pmc": t["comprador"]}, "id=?", (t["objeto_id"],))
    ctx.db.update("transferencias", {"estado": "PAGADA"}, "id=?", (t["id"],))
    ctx.log("CAMBIO_PROPIETARIO", tabla, t["objeto_id"], {"de": t["vendedor"], "a": t["comprador"], "transferencia": t["id"]})


def anular_pago(ctx: Ctx, pago_id: int, motivo: str):
    ctx.require("rec.anular")
    if not motivo.strip():
        raise ServiceError("Indique el motivo de la anulación.")
    db = ctx.db
    with db.tx():
        p = db.one("SELECT * FROM pagos WHERE id=?", (pago_id,))
        if not p or p["estado"] != "VIGENTE":
            raise ServiceError("El pago no existe o ya está anulado.")
        db.update("pagos", dict(estado="ANULADO", anulado_por=ctx.user, anulado_motivo=motivo), "id=?", (pago_id,))
        if p["liq_id"]:
            liq = db.one("SELECT * FROM liquidaciones WHERE id=?", (p["liq_id"],))
            if p["cuota_id"]:
                db.update("liq_cuotas", {"estado": "PENDIENTE"}, "id=?", (p["cuota_id"],))
            otros = db.scalar("SELECT COUNT(*) FROM pagos WHERE liq_id=? AND estado='VIGENTE'", (p["liq_id"],), 0)
            db.update("liquidaciones", {"estado": "PARCIAL" if otros else "PENDIENTE"}, "id=?", (p["liq_id"],))
            if liq["rubro"] == "IMT":
                t = db.one("SELECT * FROM transferencias WHERE id=?", (liq["objeto_id"],))
                tabla = "inmuebles" if t["tipo"] == "INM" else "vehiculos"
                db.update(tabla, {"pmc": t["vendedor"]}, "id=?", (t["objeto_id"],))
                db.update("transferencias", {"estado": "PENDIENTE"}, "id=?", (t["id"],))
        if p["cuota_id"] is None and p["detalle"] and '"plan_cuota"' in (p["detalle"] or ""):
            pass
        ctx.log("PAGO_ANULADO", "pagos", pago_id, {"motivo": motivo})


# ------------------------------------------------------------------ cuenta corriente
def cuenta_corriente(ctx: Ctx, pmc: int, incluir_no_liquidadas=True, fecha=None):
    db = ctx.db
    fecha = fecha or hoy()
    filas = []
    for l in db.all("SELECT * FROM liquidaciones WHERE pmc=? AND estado<>'ANULADA' AND estado<>'RECTIFICADA' ORDER BY gestion, rubro, id", (pmc,)):
        pagado = D(db.scalar("SELECT COALESCE(SUM(total),0) FROM pagos WHERE liq_id=? AND estado='VIGENTE'", (l["id"],), 0))
        pend = Decimal(0)
        if l["estado"] in ("PENDIENTE", "PARCIAL"):
            try:
                if l["forma_pago"] == "CUOTAS":
                    for q in db.all("SELECT * FROM liq_cuotas WHERE liq_id=? AND estado='PENDIENTE'", (l["id"],)):
                        pend += D(deuda_a_fecha(db, l, fecha, q["id"])["total"])
                else:
                    pend = D(deuda_a_fecha(db, l, fecha)["total"])
            except ServiceError:
                pend = D(l["neto"])
        filas.append(dict(gestion=l["gestion"], rubro=l["rubro"], liq_id=l["id"], nro=l["nro"], objeto=l["objeto_desc"], estado=l["estado"], impuesto=l["neto"],
                          pagado=float(pagado), a_pagar=float(rnd(pend)), origen="LIQUIDADA"))
    if incluir_no_liquidadas:
        g0, g1 = int(db.param("gestion_desde")), int(db.param("gestion_hasta"))
        ctx_ = Ctx(db, None)
        for rubro, tabla in TABLA.items():
            for o in db.all(f"SELECT id FROM {tabla} WHERE pmc=? AND estado='ACTIVO'", (pmc,)):
                for g in range(g0, g1 + 1):
                    if db.one("SELECT 1 FROM liquidaciones WHERE rubro=? AND objeto_id=? AND gestion=? AND estado NOT IN ('ANULADA','RECTIFICADA')", (rubro, o["id"], g)):
                        continue
                    try:
                        fe = db.one("SELECT contado FROM fechas_venc WHERE rubro=? AND gestion=?", ("PAF" if rubro == "PUB" else rubro, g))
                        if not fe or fe["contado"] >= fecha:
                            continue
                        pre = preliquidar(ctx_, rubro, o["id"], g)
                        if pre["neto"] <= 0:
                            continue
                        liq = {"id": 0, "pmc": pmc, "rubro": rubro, "gestion": g, "neto": pre["neto"], "forma_pago": "CONTADO", "fecha_venc": pre["fecha_venc"]}
                        tot = deuda_a_fecha(db, liq, fecha)["total"]
                        filas.append(dict(gestion=g, rubro=rubro, liq_id=None, nro="(sin liquidar)", objeto=pre["objeto_desc"], estado="NO LIQUIDADA", impuesto=pre["neto"],
                                          pagado=0.0, a_pagar=tot, origen="ESTIMADA"))
                    except ServiceError:
                        continue
    return filas


# ------------------------------------------------------------------ plan de pagos
def deuda_plan(db, liq, fecha):
    d = deuda_a_fecha(db, liq, fecha)
    return d["neto"] + d["mant_valor"] + d["interes"] + d["multa_df"] + d["sancion"]     # sin beneficio de descuento


def crear_plan(ctx: Ctx, pmc: int, liq_ids, n_cuotas: int, cuota_inicial=None, tasa=None, resolucion="", fecha=None) -> int:
    ctx.require("plan.crear")
    db = ctx.db
    fecha = fecha or hoy()
    if db.one("SELECT 1 FROM planes_pago WHERE pmc=? AND estado='VIGENTE'", (pmc,)):
        raise ServiceError("El contribuyente ya tiene un plan de pagos vigente (Art. 55 Ley 2492: facilidades por una sola vez).")
    if n_cuotas < 1 or n_cuotas > int(db.param("plan_max_cuotas", "36")):
        raise ServiceError(f"Número de cuotas fuera de rango (1–{db.param('plan_max_cuotas', '36')}).")
    items, total = [], Decimal(0)
    for lid in liq_ids:
        l = db.one("SELECT * FROM liquidaciones WHERE id=? AND pmc=?", (lid, pmc))
        if not l or l["estado"] != "PENDIENTE" or l["forma_pago"] == "CUOTAS":
            raise ServiceError(f"La liquidación {lid} no es elegible (debe estar PENDIENTE y al contado).")
        v = D(deuda_plan(db, l, fecha))
        items.append((lid, v))
        total += v
    if total <= 0:
        raise ServiceError("No hay deuda que financiar.")
    ci = D(cuota_inicial) if cuota_inicial is not None else rnd(total * D(db.param("plan_cuota_inicial_pct", "10")) / 100)
    tasa = D(tasa) if tasa is not None else D(db.param("plan_tasa_anual", "0.1082"))
    rows = generar_plan(total, ci, n_cuotas, tasa, fecha)
    with db.tx():
        pid = db.insert("planes_pago", dict(nro=numero(db, "PLAN"), pmc=pmc, fecha=fecha, deuda_total=float(rnd(total)), cuota_inicial=float(ci), n_cuotas=n_cuotas,
                                             tasa_anual=float(tasa), resolucion=resolucion, usuario=ctx.user))
        for lid, v in items:
            db.insert("plan_liqs", dict(plan_id=pid, liq_id=lid, deuda=float(rnd(v))))
            db.update("liquidaciones", {"estado": "EN_PLAN"}, "id=?", (lid,))
        if ci > 0:
            db.insert("plan_cuotas", dict(plan_id=pid, nro=0, vence=fecha, capital=float(ci), interes=0, monto=float(ci), saldo=float(rnd(total - ci))))
        for r in rows:
            db.insert("plan_cuotas", dict(plan_id=pid, **r))
        ctx.log("PLAN_PAGOS", "planes_pago", pid, {"deuda": float(total), "cuotas": n_cuotas})
    return pid


def pagar_cuota_plan(ctx: Ctx, cuota_id: int, fecha=None, modalidad="CAJA", entidad=""):
    ctx.require("rec.cobrar")
    db = ctx.db
    fecha = fecha or hoy()
    _check_fecha(ctx, fecha)
    with db.tx():
        q = db.one("SELECT * FROM plan_cuotas WHERE id=?", (cuota_id,))
        if not q or q["estado"] != "PENDIENTE":
            raise ServiceError("Cuota no encontrada o ya pagada.")
        prev = db.scalar("SELECT COUNT(*) FROM plan_cuotas WHERE plan_id=? AND nro<? AND estado='PENDIENTE'", (q["plan_id"], q["nro"]), 0)
        if prev:
            raise ServiceError("Debe pagar primero las cuotas anteriores.")
        plan = db.one("SELECT * FROM planes_pago WHERE id=?", (q["plan_id"],))
        liqs = db.all("SELECT * FROM plan_liqs WHERE plan_id=? ORDER BY liq_id", (plan["id"],))
        tot = sum(D(x["deuda"]) for x in liqs)
        recibo = numero(db, "REC")
        resto, ids = D(q["monto"]), []
        for i, x in enumerate(liqs):
            liq = db.one("SELECT * FROM liquidaciones WHERE id=?", (x["liq_id"],))
            parte = resto if i == len(liqs) - 1 else rnd(D(q["monto"]) * D(x["deuda"]) / tot)
            resto -= parte
            ids.append(db.insert("pagos", dict(nro_recibo=recibo if i == 0 else f"{recibo}-{i + 1}", liq_id=liq["id"], rubro=liq["rubro"], pmc=plan["pmc"], gestion=liq["gestion"], fecha=fecha,
                                               hora=ahora(), modalidad=modalidad, cajero=ctx.user, entidad=entidad, monto_neto=float(parte), total=float(parte),
                                               detalle=j({"plan": plan["nro"], "cuota": q["nro"], "plan_cuota": True}), usuario=ctx.user)))
        db.update("plan_cuotas", {"estado": "PAGADA", "pago_id": ids[0]}, "id=?", (cuota_id,))
        if not db.scalar("SELECT COUNT(*) FROM plan_cuotas WHERE plan_id=? AND estado='PENDIENTE'", (plan["id"],), 0):
            db.update("planes_pago", {"estado": "CUMPLIDO"}, "id=?", (plan["id"],))
            for x in liqs:
                db.update("liquidaciones", {"estado": "PAGADA"}, "id=?", (x["liq_id"],))
        ctx.log("PAGO_PLAN", "plan_cuotas", cuota_id, {"recibo": recibo, "monto": q["monto"]})
    return ids[0]


# ------------------------------------------------------------------ conciliación bancaria
def conciliar_banco(ctx: Ctx, filas, entidad: str):
    """filas: iterable de dicts {codigo_pago, monto, fecha}. Registra los pagos que cuadran; devuelve (ok, observados)."""
    ctx.require("rec.cobrar")
    ok, obs = [], []
    for f in filas:
        cod = str(f.get("codigo_pago", "")).strip()
        liq = ctx.db.one("SELECT * FROM liquidaciones WHERE codigo_pago=?", (cod,))
        if not liq:
            obs.append((cod, "Código de pago inexistente")); continue
        try:
            fecha = str(f.get("fecha") or hoy())[:10]
            d = deuda_a_fecha(ctx.db, liq, fecha)
            if abs(d["total"] - float(f["monto"])) > 0.5:
                obs.append((cod, f"Monto banco {float(f['monto']):,.2f} ≠ calculado {d['total']:,.2f}")); continue
            if liq["estado"] not in ("PENDIENTE", "PARCIAL"):
                obs.append((cod, f"Liquidación {liq['estado']}")); continue
            ok.append((cod, cobrar(ctx, liq["id"], fecha, "BANCO", entidad)))
        except ServiceError as e:
            obs.append((cod, str(e)))
    return ok, obs
