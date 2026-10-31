"""Liquidación de IPBI, IPVA, Patente (PAF), Publicidad e IMT; rectificatorias; liquidación masiva y deuda a una fecha."""
from datetime import date
from decimal import Decimal

from ..calc.deuda import calcular_deuda
from ..calc.imt import calcular_imt
from ..calc.ipbi import CalcError, calcular_ipbi
from ..calc.ipva import calcular_ipva
from ..calc.patentes import calcular_paf, calcular_publicidad, meses_en_gestion
from ..calc.util import D, rnd
from .base import Ctx, ServiceError, ahora, codigo_pago, cotizacion, deuda_params, hoy, j, numero, row_dict, tasa_interes

TABLA = {"IPBI": "inmuebles", "IPVA": "vehiculos", "PAF": "actividades", "PUB": "publicidad"}
CON_DESCUENTO = ("IPBI", "IPVA", "PAF", "PUB")
PREFIJO = {"IPBI": "F1980", "IPVA": "F2160", "PAF": "F501", "PUB": "F501P", "IMT": "F502"}


def _persona(db, pmc):
    r = db.one("SELECT persona, benemerito FROM contribuyentes WHERE pmc=?", (pmc,))
    return (r["persona"] if r else "N"), bool(r["benemerito"]) if r else False


def descripcion_objeto(rubro, o) -> str:
    if rubro == "IPBI":
        return f"{o['tipo']} – {o['tipo_via'] or ''} {o['calle'] or ''} {o['numero'] or ''} (Zona {o['zona'] or '-'}) Cód.Cat. {o['cod_catastral'] or '-'}".strip()
    if rubro == "IPVA":
        return f"{o['tipo']} {o['marca'] or ''} {o['modelo'] or ''} {o['anio_fab']} – Placa {o['placa']}".strip()
    if rubro == "PAF":
        return f"{o['nombre_comercial'] or 'Actividad'} (Act {o['act']}-{o['cat']}) – {o['calle'] or ''} {o['numero'] or ''}".strip()
    return f"{o['tipo']} – {o['descripcion'] or ''} {o['ubicacion'] or ''}".strip()


def fechas(db, rubro, gestion):
    r = db.one("SELECT * FROM fechas_venc WHERE rubro=? AND gestion=?", ("PAF" if rubro == "PUB" else rubro, gestion))
    if not r or not r["contado"]:
        raise ServiceError(f"No están cargadas las fechas de vencimiento de {rubro} para la gestión {gestion} (Mantenimiento ▸ Fechas de vencimiento).")
    return row_dict(r)


def preliquidar(ctx: Ctx, rubro: str, obj_id: int, gestion: int, forma_pago="CONTADO", tipo_liq="ORIGINAL") -> dict:
    db = ctx.db
    if rubro not in TABLA:
        raise ValueError(rubro)
    o = db.one(f"SELECT * FROM {TABLA[rubro]} WHERE id=?", (obj_id,))
    if not o:
        raise ServiceError("Registro no encontrado.")
    c = db.one("SELECT * FROM contribuyentes WHERE pmc=?", (o["pmc"],))
    if c["estado"] != "ACTIVO":
        raise ServiceError("El contribuyente está INCOMPLETO. Complete sus datos (Mantenimiento ▸ Registros incompletos).")
    fe = fechas(db, rubro, gestion)
    persona, bene = c["persona"], bool(c["benemerito"])
    try:
        if rubro == "IPBI":
            det = calcular_ipbi(db, o, gestion, persona, bene)
        elif rubro == "IPVA":
            det = calcular_ipva(db, o, gestion, persona)
        elif rubro == "PAF":
            det = calcular_paf(db, o, gestion)
        else:
            det = calcular_publicidad(db, o, gestion)
    except CalcError as e:
        raise ServiceError(str(e))
    impuesto = D(det["impuesto"])
    previas = db.all("SELECT * FROM liquidaciones WHERE rubro=? AND objeto_id=? AND gestion=? AND estado NOT IN ('ANULADA','RECTIFICADA') ORDER BY id", (rubro, obj_id, gestion))
    if tipo_liq == "ORIGINAL" and previas:
        raise ServiceError(f"Ya existe una liquidación {previas[-1]['nro']} para esta gestión ({previas[-1]['estado']}). Use 'Rectificatoria'.")
    if tipo_liq == "RECTIFICATORIA" and not previas:
        raise ServiceError("No existe liquidación original que rectificar.")
    credito = Decimal(0)
    for p in previas:
        credito += D(db.scalar("SELECT COALESCE(SUM(monto_neto),0) FROM pagos WHERE liq_id=? AND estado='VIGENTE'", (p["id"],), 0))
    neto = max(Decimal(0), impuesto - credito)
    if credito > impuesto:
        det["saldo_favor"] = float(rnd(credito - impuesto))
    cuotas = []
    if forma_pago == "CUOTAS":
        if not fe.get("cuota1") or not fe.get("cuota2"):
            raise ServiceError("No hay fechas de cuotas cargadas para esta gestión.")
        m1 = rnd(neto / 2)
        cuotas = [dict(nro=1, monto=float(m1), vence=fe["cuota1"]), dict(nro=2, monto=float(rnd(neto - m1)), vence=fe["cuota2"])]
    return dict(rubro=rubro, pmc=o["pmc"], objeto_id=obj_id, objeto_desc=descripcion_objeto(rubro, o), gestion=gestion, tipo_liq=tipo_liq,
                forma_pago=forma_pago, base_imponible=det.get("base_imponible", 0), impuesto=float(rnd(impuesto)), credito=float(rnd(credito)),
                neto=float(rnd(neto)), fecha_venc=fe["contado"], cuotas=cuotas, detalle=det, previas=[p["id"] for p in previas], fechas=fe)


def guardar_liquidacion(ctx: Ctx, pre: dict) -> int:
    ctx.require("liq.ejecutar")
    db = ctx.db
    with db.tx():
        nro = numero(db, PREFIJO[pre["rubro"]])
        lid = db.insert("liquidaciones", dict(
            nro=nro, rubro=pre["rubro"], pmc=pre["pmc"], objeto_id=pre["objeto_id"], objeto_desc=pre["objeto_desc"], gestion=pre["gestion"],
            tipo_liq=pre["tipo_liq"], forma_pago=pre["forma_pago"], base_imponible=pre["base_imponible"], impuesto=pre["impuesto"], credito=pre["credito"],
            neto=pre["neto"], fecha=hoy(), hora=ahora(), fecha_venc=pre["fecha_venc"], estado="PENDIENTE" if pre["neto"] > 0 else "PAGADA",
            detalle=j(pre["detalle"]), usuario=ctx.user))
        db.update("liquidaciones", {"codigo_pago": codigo_pago(pre["rubro"], pre["gestion"], lid)}, "id=?", (lid,))
        for q in pre["cuotas"]:
            db.insert("liq_cuotas", dict(liq_id=lid, nro=q["nro"], monto=q["monto"], vence=q["vence"]))
        for pid in pre["previas"]:
            db.update("liquidaciones", {"estado": "RECTIFICADA", "rectifica_a": lid}, "id=?", (pid,))
            db.execute("UPDATE liq_cuotas SET estado='ANULADA' WHERE liq_id=? AND estado='PENDIENTE'", (pid,))
        ctx.log("LIQUIDACION", "liquidaciones", lid, {"nro": nro, "rubro": pre["rubro"], "neto": pre["neto"]})
    return lid


def liquidar(ctx, rubro, obj_id, gestion, forma_pago="CONTADO", tipo_liq="ORIGINAL") -> int:
    return guardar_liquidacion(ctx, preliquidar(ctx, rubro, obj_id, gestion, forma_pago, tipo_liq))


# --------------------------------------------------------------------------------------------
def deuda_a_fecha(db, liq, fecha_pago=None, cuota_id=None) -> dict:
    """Importe a pagar en `fecha_pago` (descuento 10%, o accesorios de la Deuda Tributaria si está en mora)."""
    fecha_pago = str(fecha_pago or hoy())[:10]
    persona, _ = _persona(db, liq["pmc"])
    base = dict(liq_id=liq["id"], fecha_pago=fecha_pago, neto=0.0, descuento=0.0, mant_valor=0.0, interes=0.0, multa_df=0.0, sancion=0.0, total=0.0,
                mora=0, concepto="", en_mora=False)
    rubro = liq["rubro"]
    cuota = None
    if cuota_id:
        cuota = db.one("SELECT * FROM liq_cuotas WHERE id=? AND liq_id=?", (cuota_id, liq["id"]))
        if not cuota or cuota["estado"] != "PENDIENTE":
            raise ServiceError("La cuota no existe o ya fue pagada.")
        monto, fv, fsa, contado = D(cuota["monto"]), cuota["vence"], cuota["vence"], None
        base["concepto"] = f"Cuota {cuota['nro']}"
    else:
        monto = D(liq["neto"])
        if rubro == "IMT":
            fv = fsa = liq["fecha_venc"]; contado = None
        else:
            fe = fechas(db, rubro, liq["gestion"])
            contado = fe["contado"]
            fsa = fe["sin_accesorios"] or contado
            fv = fsa
        if liq["forma_pago"] == "CUOTAS":
            raise ServiceError("Esta liquidación es en dos cuotas: pague cada cuota por separado.")
    base["neto"] = float(rnd(monto))
    if monto <= 0:
        return base
    pct = D(db.param("descuento_contado", "10")) / 100
    if contado and not cuota and rubro in CON_DESCUENTO and liq["forma_pago"] == "CONTADO" and fecha_pago <= contado:
        desc = rnd(monto * pct)
        base.update(descuento=float(desc), total=float(rnd(monto - desc)), concepto="Pago al contado con descuento")
        return base
    if fecha_pago <= fsa:
        base.update(total=float(rnd(monto)), concepto=base["concepto"] or "Pago sin descuento ni accesorios")
        return base
    # --- en mora: Deuda Tributaria
    _, ufv_fv, _ = cotizacion(db, fv)
    usd_fp, ufv_fp, _ = cotizacion(db, fecha_pago)
    p = deuda_params(db, persona)
    p.r = tasa_interes(db, fecha_pago)
    kw = {}
    if date.fromisoformat(fv) < date(2002, 12, 26):
        usd_fv, _, _ = cotizacion(db, fv)
        usd_26, ufv_26, _ = cotizacion(db, "2002-12-26")
        kw = dict(usd_fv=usd_fv, usd_26=usd_26, ufv_26=ufv_26)
        usd_fv_ = usd_fv
    d = calcular_deuda(monto, fv, fecha_pago, ufv_fv, ufv_fp, p, **kw)
    base.update(mant_valor=float(d.mv), interes=float(d.interes), multa_df=float(d.multa_bs), sancion=float(d.sancion), total=float(d.total), mora=d.mora,
                en_mora=True, concepto=(base["concepto"] + " – " if base["concepto"] else "") + f"Deuda tributaria ({d.mora} días de mora)",
                ufv_fv=float(ufv_fv), ufv_fp=float(ufv_fp), r=float(p.r), multa_ufv=float(d.multa_ufv), fv=fv)
    return base


# --------------------------------------------------------------------------------------------
def liquidar_masiva(ctx: Ctx, rubro: str, gestion: int, zona=None, barrio=None, pmc=None, guardar=False, solo_vencidas=True):
    """Preliquida (y opcionalmente guarda) a todos los contribuyentes sin liquidación vigente en la gestión. Devuelve (filas, errores)."""
    ctx.require("liq.masiva")
    db = ctx.db
    tabla = TABLA[rubro]
    q = f"SELECT o.id, o.pmc FROM {tabla} o JOIN contribuyentes c ON c.pmc=o.pmc WHERE o.estado='ACTIVO' AND c.estado='ACTIVO'"
    p = []
    if zona:
        q += " AND o.zona=?"; p.append(zona)
    if barrio:
        q += " AND o.barrio=?"; p.append(barrio)
    if pmc:
        q += " AND o.pmc=?"; p.append(int(pmc))
    if solo_vencidas:
        try:
            if fechas(db, rubro, gestion)["contado"] >= hoy() and not pmc:
                return [], [("-", "La gestión aún no vence; no hay evasores. Desmarque 'sólo vencidas' para preliquidar.")]
        except ServiceError as e:
            return [], [("-", str(e))]
    rows, errs = [], []
    for r in db.all(q + " ORDER BY o.pmc, o.id", p):
        ya = db.one("SELECT id FROM liquidaciones WHERE rubro=? AND objeto_id=? AND gestion=? AND estado NOT IN ('ANULADA','RECTIFICADA')", (rubro, r["id"], gestion))
        if ya:
            continue
        try:
            pre = preliquidar(ctx, rubro, r["id"], gestion)
            if pre["neto"] <= 0:
                continue
            lid = guardar_liquidacion(ctx, pre) if guardar else None
            liq = {"id": lid or 0, "pmc": r["pmc"], "rubro": rubro, "gestion": gestion, "neto": pre["neto"], "forma_pago": "CONTADO", "fecha_venc": pre["fecha_venc"]}
            try:
                d = deuda_a_fecha(db, liq, hoy())
            except ServiceError:
                d = dict(total=pre["neto"], mora=0)
            rows.append(dict(pmc=r["pmc"], objeto_id=r["id"], descripcion=pre["objeto_desc"], gestion=gestion, neto=pre["neto"], total_hoy=d["total"], mora=d["mora"], liq_id=lid))
        except ServiceError as e:
            errs.append((r["pmc"], f"{TABLA[rubro]} #{r['id']}: {e}"))
    return rows, errs


# --------------------------------------------------------------------------------------------
def base_ultima_gestion(db, tipo, obj_id, anio_ref: int):
    """Base imponible IPBI/IPVA de la última gestión vencida (insumo del IMT)."""
    rubro, tabla = ("IPBI", "inmuebles") if tipo == "INM" else ("IPVA", "vehiculos")
    o = db.one(f"SELECT * FROM {tabla} WHERE id=?", (obj_id,))
    c = db.one("SELECT persona FROM contribuyentes WHERE pmc=?", (o["pmc"],))
    for g in range(anio_ref - 1, anio_ref - 8, -1):
        try:
            det = calcular_ipbi(db, o, g, c["persona"]) if tipo == "INM" else calcular_ipva(db, o, g, c["persona"])
            return det["base_imponible"], g
        except CalcError:
            continue
    return 0.0, None


def liquidar_imt(ctx: Ctx, tipo: str, vendedor: int, comprador: int, objeto_id: int, fecha_minuta: str, monto_bs: float, monto_usd=0.0, extras=None):
    ctx.require("liq.ejecutar")
    db = ctx.db
    if vendedor == comprador:
        raise ServiceError("Vendedor y comprador no pueden ser el mismo contribuyente.")
    tabla = "inmuebles" if tipo == "INM" else "vehiculos"
    o = db.one(f"SELECT * FROM {tabla} WHERE id=? AND estado='ACTIVO'", (objeto_id,))
    if not o or o["pmc"] != vendedor:
        raise ServiceError("El bien no está registrado (activo) a nombre del vendedor.")
    if not db.one("SELECT 1 FROM contribuyentes WHERE pmc=? AND estado='ACTIVO'", (comprador,)):
        raise ServiceError("El comprador debe estar empadronado (ACTIVO). Regístrelo con F-019.")
    if db.one("SELECT 1 FROM transferencias WHERE tipo=? AND objeto_id=? AND estado='PENDIENTE'", (tipo, objeto_id)):
        raise ServiceError("Ya existe una transferencia pendiente de pago para este bien.")
    anio = int(str(fecha_minuta)[:4])
    base_g, g = base_ultima_gestion(db, tipo, objeto_id, anio)
    calc = calcular_imt(db, monto_bs, base_g, fecha_minuta)
    calc["gestion_base"] = g
    with db.tx():
        ex = extras or {}
        tid = db.insert("transferencias", dict(tipo=tipo, vendedor=vendedor, comprador=comprador, objeto_id=objeto_id, fecha_minuta=fecha_minuta, monto_usd=monto_usd,
                                               monto_bs=monto_bs, fecha=hoy(), usuario=ctx.user, **{k: ex.get(k) for k in ("nro_ddrr", "fecha_ddrr", "sup_total", "sup_construida", "nro_poliza", "fecha_poliza", "color", "nro_motor", "nro_chasis")}))
        nro = numero(db, PREFIJO["IMT"])
        lid = db.insert("liquidaciones", dict(nro=nro, rubro="IMT", pmc=vendedor, objeto_id=tid, objeto_desc=descripcion_objeto("IPBI" if tipo == "INM" else "IPVA", o), gestion=anio,
                                               base_imponible=calc["base_imponible"], impuesto=calc["impuesto"], neto=calc["impuesto"], fecha=hoy(), hora=ahora(),
                                               fecha_venc=calc["fecha_limite"], estado="PENDIENTE", detalle=j({**calc, "tipo": tipo, "comprador": comprador}), usuario=ctx.user))
        db.update("liquidaciones", {"codigo_pago": codigo_pago("IMT", anio, lid)}, "id=?", (lid,))
        db.update("transferencias", {"liq_id": lid}, "id=?", (tid,))
        ctx.log("IMT_LIQUIDACION", "transferencias", tid, calc)
    return lid, tid
