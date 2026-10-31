import pytest

from siim.calc.ipbi import calcular_ipbi
from siim.core import security
from siim.services import liquidacion as L, otros, padron, recaudacion as R
from siim.services.base import Ctx, ServiceError


def test_ipbi_casa_perez(ctx, ids):
    p = L.preliquidar(ctx, "IPBI", ids["inm_perez"], 2004)
    d = p["detalle"]
    assert d["valor_terreno"] == 250 * 75              # asfalto zona A, servicios completos, plano
    assert d["valor_construccion"] == pytest.approx(180 * 680 * 0.975)
    assert p["base_imponible"] == pytest.approx(138090.0)
    assert p["neto"] == pytest.approx(round(0.0035 * (138090 - 1), 2))


def test_ipbi_tramos_y_exenciones(ctx, ids):
    assert L.preliquidar(ctx, "IPBI", ids["inm_bene"], 2004)["neto"] == 0        # benemérito: base menor al tope del 1er tramo
    assert L.preliquidar(ctx, "IPBI", ids["inm_rural"], 2004)["neto"] == 300      # 0,20% de 150.000
    big = L.preliquidar(ctx, "IPBI", ids["inm_fideos"], 2004)
    assert big["base_imponible"] == 595000
    assert big["neto"] == pytest.approx(1193 + 0.005 * (595000 - 340972), abs=0.01)


def test_ipva(ctx, ids):
    p = L.preliquidar(ctx, "IPVA", ids["veh_perez"], 2004)     # vagoneta japonesa 4200cc doble tracción, 3 años
    assert p["base_imponible"] == pytest.approx(182382 * 1.15 * 0.41, abs=0.5)
    assert p["neto"] == pytest.approx(829 + 0.02 * (p["base_imponible"] - 41475), abs=0.01)
    m = L.preliquidar(ctx, "IPVA", ids["veh_moto"], 2004)
    assert m["detalle"]["codigo"] == 52                          # 250 cc → rango 250–349
    assert m["neto"] > 0


def test_paf_modalidades_y_duodecimas(ctx, ids):
    f = L.preliquidar(ctx, "PAF", ids["act_farm"], 2004)
    assert f["neto"] == 4500 * 70 / 100                     # Zona 1, 45 m² → 70 %
    t = L.preliquidar(ctx, "PAF", ids["act_tienda"], 2004)
    assert t["detalle"]["duodecimas"] == "6/12" and t["neto"] == pytest.approx(600 * 0.30 * 6 / 12)
    ctx.db.set_param("patente_modalidad", "CATEGORIA")
    assert L.preliquidar(ctx, "PAF", ids["act_farm"], 2004)["neto"] == 1400
    ctx.db.set_param("patente_modalidad", "PUA")
    pua = L.preliquidar(ctx, "PAF", ids["act_farm"], 2004)
    assert pua["neto"] == min(45 * 12, 4500)


def test_pago_contado_con_descuento_y_mora(ctx, ids):
    lid = L.liquidar(ctx, "IPBI", ids["inm_perez"], 2004)
    liq = ctx.db.one("SELECT * FROM liquidaciones WHERE id=?", (lid,))
    d1 = L.deuda_a_fecha(ctx.db, liq, "2005-03-31")
    assert d1["descuento"] == pytest.approx(liq["neto"] * 0.10, abs=0.01) and not d1["en_mora"]
    d2 = L.deuda_a_fecha(ctx.db, liq, "2005-04-20")                # entre contado y 'sin accesorios'
    assert d2["total"] == liq["neto"] and d2["descuento"] == 0
    d3 = L.deuda_a_fecha(ctx.db, liq, "2005-04-21")
    assert d3["en_mora"] is False                                  # el 21/04 aún sin accesorios (límite 30/04)
    d4 = L.deuda_a_fecha(ctx.db, liq, "2005-06-30")
    assert d4["en_mora"] and d4["mora"] == 61 and d4["total"] > liq["neto"]
    assert d4["mant_valor"] > 0 and d4["interes"] >= 0
    pid = R.cobrar(ctx, lid, "2005-03-31", importe_recibido=d1["total"])
    assert ctx.db.one("SELECT estado FROM liquidaciones WHERE id=?", (lid,))["estado"] == "PAGADA"
    with pytest.raises(ServiceError):
        R.cobrar(ctx, lid, "2005-03-31")                           # no se cobra dos veces
    R.anular_pago(ctx, pid, "error de caja")
    assert ctx.db.one("SELECT estado FROM liquidaciones WHERE id=?", (lid,))["estado"] == "PENDIENTE"


def test_dos_cuotas_y_rectificatoria(ctx, ids):
    lid = L.liquidar(ctx, "PAF", ids["act_ferr"], 2004, "CUOTAS")
    q = ctx.db.all("SELECT * FROM liq_cuotas WHERE liq_id=? ORDER BY nro", (lid,))
    assert len(q) == 2 and sum(x["monto"] for x in q) == pytest.approx(3200)
    R.cobrar(ctx, lid, "2005-03-31", cuota_id=q[0]["id"])
    assert ctx.db.one("SELECT estado FROM liquidaciones WHERE id=?", (lid,))["estado"] == "PARCIAL"
    with pytest.raises(ServiceError):
        L.liquidar(ctx, "PAF", ids["act_ferr"], 2004)               # original duplicada
    ctx.db.update("actividades", {"superficie": 200}, "id=?", (ids["act_ferr"],))   # corrección de superficie
    pre = L.preliquidar(ctx, "PAF", ids["act_ferr"], 2004, "CONTADO", "RECTIFICATORIA")
    assert pre["credito"] == pytest.approx(1600) and pre["neto"] == pytest.approx(4000 * 0.9 - 1600)


def test_imt_transferencia(ctx, ids):
    lid, tid = L.liquidar_imt(ctx, "INM", ids["perez"], ids["lopez"], ids["inm_perez"], "2005-02-10", 400000, 49000)
    liq = ctx.db.one("SELECT * FROM liquidaciones WHERE id=?", (lid,))
    assert liq["impuesto"] == pytest.approx(12000)                  # 3% × 400.000 (mayor que la base 2004)
    assert liq["fecha_venc"] == "2005-02-24"                        # 10 días hábiles
    R.cobrar(ctx, lid, "2005-02-15")
    assert ctx.db.one("SELECT pmc FROM inmuebles WHERE id=?", (ids["inm_perez"],))["pmc"] == ids["lopez"]
    R.anular_pago(ctx, ctx.db.scalar("SELECT id FROM pagos WHERE liq_id=?", (lid,)), "devolución")
    assert ctx.db.one("SELECT pmc FROM inmuebles WHERE id=?", (ids["inm_perez"],))["pmc"] == ids["perez"]


def test_plan_de_pagos(ctx, ids):
    lid = L.liquidar(ctx, "IPBI", ids["inm_fideos"], 2004)
    plan = R.crear_plan(ctx, ids["fideos"], [lid], 6, fecha="2005-06-30")
    cuotas = ctx.db.all("SELECT * FROM plan_cuotas WHERE plan_id=? ORDER BY nro", (plan,))
    assert cuotas[0]["nro"] == 0 and len(cuotas) == 7
    with pytest.raises(ServiceError):
        R.crear_plan(ctx, ids["fideos"], [lid], 6)                  # una sola vez
    for q in cuotas:
        R.pagar_cuota_plan(ctx, q["id"], "2005-07-01")
    assert ctx.db.one("SELECT estado FROM liquidaciones WHERE id=?", (lid,))["estado"] == "PAGADA"
    assert ctx.db.one("SELECT estado FROM planes_pago WHERE id=?", (plan,))["estado"] == "CUMPLIDO"


def test_masiva_y_cuenta_corriente(ctx, ids):
    rows, errs = L.liquidar_masiva(ctx, "IPBI", 2004, guardar=True)
    assert len(rows) >= 4 and not [e for e in errs if "Falta" not in e[1]]
    cc = R.cuenta_corriente(ctx, ids["perez"])
    assert any(f["rubro"] == "IPBI" and f["a_pagar"] > 0 for f in cc)


def test_fuc(ctx):
    fid = otros.crear_fuc(ctx, "Juan Pérez", [{"subnivel": "151003.002", "cantidad": 10}, {"subnivel": "151003.001", "cantidad": 1}])
    assert ctx.db.one("SELECT total FROM fuc WHERE id=?", (fid,))["total"] == 35
    otros.recaudar_fuc(ctx, fid)
    with pytest.raises(ServiceError):
        otros.borrar_fuc(ctx, fid)
    otros.anular_fuc(ctx, fid, "duplicado")


def test_conciliacion_bancaria(ctx, ids):
    lid = L.liquidar(ctx, "IPVA", ids["veh_lopez"], 2004)
    liq = ctx.db.one("SELECT * FROM liquidaciones WHERE id=?", (lid,))
    d = L.deuda_a_fecha(ctx.db, liq, "2005-03-30")
    ok, obs = R.conciliar_banco(ctx, [dict(codigo_pago=liq["codigo_pago"], monto=d["total"], fecha="2005-03-30"), dict(codigo_pago="X999", monto=1)], "Banco Unión")
    assert len(ok) == 1 and len(obs) == 1


def test_permisos_y_empadronamiento(db, ids):
    security.create_user(db, "caja", "Cajero", "CAJERO", "Caja12345")
    ses = security.login(db, "caja", "Caja12345")
    c = Ctx(db, ses)
    with pytest.raises(ServiceError):
        padron.nuevo_contribuyente(c, {"persona": "N"})
    with pytest.raises(ServiceError):
        L.liquidar(c, "IPBI", ids["inm_perez"], 2004)


def test_baja_f035_y_licencias(ctx, ids):
    nro, vence = padron.emitir_licencia(ctx, ids["act_farm"], "2005-01-15")
    assert nro.startswith("LF-2005") and vence == "2006-01-15"
    padron.baja_objeto(ctx, "actividades", ids["act_farm"], "2005-02-01", "cierre")
    a = ctx.db.one("SELECT * FROM actividades WHERE id=?", (ids["act_farm"],))
    assert a["estado"] == "INACTIVO" and a["fecha_cese"] == "2005-02-01" and a["estado_licencia"] == "CANCELADA"
    ok, _ = security.verify_audit_chain(ctx.db)
    assert ok


def test_importar_padron_excel(ctx, tmp_path):
    from siim.services import importar
    from openpyxl import load_workbook
    f = tmp_path / "p.xlsx"
    importar.plantilla(f)
    wb = load_workbook(f)
    c = wb["contribuyentes"]; c.delete_rows(2)
    c.append(["N", "CI", "9001", "LP", "Rojas", "Apaza", "Luis", None, None, "A", None, "CALLE", "Sucre", "10"])
    c.append(["N", "CI", "9002", "LP", None, None, None, None, None, "A", None, "CALLE", "X", "1"])          # incompleto → error
    a = wb["actividades"]; a.delete_rows(2)
    a.append(["9001", "14", "02", "Ferretería Rojas", None, None, None, "2020-01-15", None, 30, None, "2", None, None, "Sucre", "10"])
    for h in ("inmuebles", "vehiculos", "publicidad"):
        wb[h].delete_rows(2)
    wb.save(f)
    r = importar.importar_padron(ctx, f, simular=True)
    assert r["resumen"]["contribuyentes"] == 1 and len(r["errores"]) == 1 and ctx.db.scalar("SELECT COUNT(*) FROM contribuyentes") == 0
    r = importar.importar_padron(ctx, f, simular=False)
    assert ctx.db.scalar("SELECT COUNT(*) FROM contribuyentes") == 1 and ctx.db.scalar("SELECT COUNT(*) FROM actividades") == 1
