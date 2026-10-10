"""CASO 2 (E2E): SERVICIO de mantenimiento por Bs 32.000 con Consulta de Precios SICOES (Formulario 110).

Cuantia entre Bs 20.001 y 50.000 -> Formulario 110 obligatorio, 3 cotizaciones minimas, margen de preferencia MyPE,
sobres sellados y formalizacion segun el plazo (12 dias = Orden de Servicio; 20 dias = Contrato Administrativo).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import ContratacionMenor
from tests.helpers import Flujo, ahora_mas

OBJETO = "Mantenimiento correctivo de las instalaciones eléctricas del edificio municipal"


def preparar_en_cotizacion(f: Flujo, plazo: int):
    c = f.crear(OBJETO, "SERVICIO_GENERAL", plazo, unidad_solicitante="Unidad Administrativa")
    cid = c["id"]
    d = f.item(cid, "25800", "Mantenimiento correctivo de instalaciones eléctricas (mano de obra y materiales)",
               "Global", 1, "32000.00").json()
    assert Decimal(d["monto_referencial_total"]) == Decimal("32000.00")
    assert d["modalidad_cuantia"] == "CONSULTA_PRECIOS_SICOES"
    assert d["items"][0]["estado_chb"] == "NO_APLICA"
    c = f.accion(cid, "solicitar", "solicitante").json()
    assert c["estado"] == "SOLICITADO" and c["requiere_excepcion_chb"] is False
    assert {x["tipo_doc"] for x in c["documentos"]} == {"C1_SOLICITUD"}  # sin informe CHB: no es un bien
    f.accion(cid, "certificar", "presupuesto", json={"preventivo_c31_nro": "C31-2026-00456"})
    c = f.accion(cid, "aprobar-inicio", "rpa").json()
    assert c["estado"] == "EN_COTIZACION"
    return cid


def cotizar(f, cid, nit, razon, monto, plazo, esperado=201):
    return f.req("POST", f"/contrataciones/{cid}/cotizaciones", "contrataciones", esperado, json={
        "nit_ci": nit, "razon_social": razon, "monto_total_ofertado": str(monto), "plazo_ofertado_dias": plazo,
        "correo": "oferta@proveedor.bo", "telefono": "71234567"})


def vencer_plazo(SessionTest, cid):
    with SessionTest() as s:
        c = s.scalar(select(ContratacionMenor).where(ContratacionMenor.id == __import__("uuid").UUID(cid)))
        c.fecha_limite_ofertas = datetime.now(timezone.utc) - timedelta(minutes=5)
        s.commit()


def test_caso2_servicio_32000_consulta_de_precios(client, tokens, SessionTest):
    f = Flujo(client, tokens)
    cid = preparar_en_cotizacion(f, plazo=12)

    # sin Formulario 110 no se pueden ni emitir fichas ni cargar cotizaciones
    r = cotizar(f, cid, "1111111111", "SIN F110", "30000", 10, 422)
    assert r.json()["detail"]["codigo"] == "FORMULARIO_110_REQUERIDO"
    r = f.req("POST", f"/contrataciones/{cid}/fichas-cotizacion", "contrataciones", 422,
              json={"destinatarios": [{"razon_social": "PROVEEDOR XY"}], "canales": ["IMPRESO"]})
    assert r.json()["detail"]["codigo"] == "FORMULARIO_110_REQUERIDO"

    # Formulario 110 con plazo de presentacion
    c = f.req("PUT", f"/contrataciones/{cid}/formulario-110", "contrataciones", 200, json={
        "nro_formulario_110": "F110-2026-000457", "fecha_limite_ofertas": ahora_mas(hours=2)}).json()
    assert c["nro_formulario_110"] == "F110-2026-000457"

    # fichas multicanal: impreso, WhatsApp (enlace) y correo (sin SMTP configurado)
    r = f.req("POST", f"/contrataciones/{cid}/fichas-cotizacion", "contrataciones", 200, json={
        "destinatarios": [{"razon_social": "ELECTRO SERVICIOS S.R.L.", "correo": "ventas@electro.bo", "telefono": "71234567"}],
        "canales": ["IMPRESO", "WHATSAPP", "EMAIL"]}).json()
    canales = r["resultados"][0]["canales"]
    assert canales["WHATSAPP"].startswith("https://wa.me/59171234567?text=")
    assert canales["EMAIL"] == "NO_CONFIGURADO" and canales["IMPRESO"] == r["documento_id"]

    # ofertas (sobres sellados)
    cotizar(f, cid, "1020304050", "ELECTRO SERVICIOS S.R.L.", "31500.00", 12)
    qb = cotizar(f, cid, "2030405060", "INSTALACIONES BOLIVIA LTDA. (MyPE)", "30800.00", 10).json()
    qc = cotizar(f, cid, "3040506070", "MANTENIMIENTO INTEGRAL S.A.", "29900.00", 12).json()
    qd = cotizar(f, cid, "4050607080", "OFERTAS BARATAS S.R.L.", "28000.00", 12).json()

    # el plazo aun no vence: no se pueden abrir los sobres
    r = f.accion(cid, "abrir-ofertas", "contrataciones", 422)
    assert r.json()["detail"]["codigo"] == "PLAZO_VIGENTE"
    vencer_plazo(SessionTest, cid)
    f.accion(cid, "abrir-ofertas", "contrataciones")

    # calificacion: D no cumple; B tiene registro MyPE valido (margen 5%)
    cal = lambda q, **kw: f.req("PATCH", f"/contrataciones/{cid}/cotizaciones/{q['id']}", "contrataciones", 200, json=kw)
    c = f.detalle(cid)
    por_nit = {q["nit_ci"]: q for q in c["cotizaciones"]}
    cal(por_nit["1020304050"], cumple_especificaciones=True)
    cal(qb, cumple_especificaciones=True, registro_preferencia="MYPE", registro_preferencia_valido=True,
        margen_preferencia_pct="5")
    cal(qc, cumple_especificaciones=True)
    cal(qd, cumple_especificaciones=False, observaciones="No presenta certificado de idoneidad")

    m = f.req("GET", f"/contrataciones/{cid}/evaluacion", "contrataciones", 200).json()
    ranking = [(o["razon_social"], o["ranking"], o["precio_evaluado"]) for o in m["ofertas"]]
    # B (30.800 con 5% = 29.260) supera a C (29.900) gracias al margen de preferencia; D queda excluida
    assert ranking[0][0].startswith("INSTALACIONES BOLIVIA") and ranking[0][2] in ("29260.00", "29260")
    assert [r[1] for r in ranking] == [1, 2, 3, None] and m["ofertas"][3]["elegible"] is False
    assert m["recomendada"] == qb["id"] and m["hay_desempate"] is False

    c = f.accion(cid, "evaluar", "contrataciones").json()
    assert c["estado"] == "EVALUADO"
    # adjudicar otra oferta exige fundamentar; una no elegible no se puede adjudicar
    f.accion(cid, "adjudicar", "rpa", 422, json={"cotizacion_id": qc["id"]})
    f.accion(cid, "adjudicar", "rpa", 422, json={"cotizacion_id": qd["id"], "motivo": "Preferimos la más barata del mercado"})
    c = f.accion(cid, "adjudicar", "rpa", json={}).json()
    assert c["estado"] == "ADJUDICADO"

    # formalizacion: CUCE obligatorio en consulta de precios; plazo 12 dias => Orden de Servicio
    r = f.accion(cid, "formalizar", "rpa", 422, json={})
    assert any("CUCE" in e for e in r.json()["detail"]["errores"])
    c = f.accion(cid, "formalizar", "rpa", json={"cuce": "26-1234-00-1234567-1-1"}).json()
    assert c["estado"] == "FORMALIZADO" and c["metodo_formalizacion"] == "ORDEN_SERVICIO"

    hoy = __import__("datetime").date.today().isoformat()
    c = f.accion(cid, "recepcion", "recepcion", json={"fecha_recepcion": hoy, "conforme": True}).json()
    assert c["estado"] == "RECEPCIONADO" and c["recepciones"][0]["nro_nia"].startswith("IC-")  # informe de conformidad
    c = f.accion(cid, "devengar", "presupuesto").json()
    assert c["estado"] == "DEVENGADO"
    # reservado 32.000; devengado = monto ofertado de B (30.800): se liberan 1.200
    assert Decimal(f.partida("25800")["saldo_disponible"]) == Decimal("45000") - Decimal("32000") + Decimal("1200")
    assert {x["tipo_doc"] for x in c["documentos"]} >= {
        "C1_SOLICITUD", "CERTIFICACION_C31", "FICHA_COTIZACION", "CUADRO_COMPARATIVO", "NOTA_ADJUDICACION",
        "ORDEN_COMPRA_SERVICIO", "ACTA_RECEPCION_FORM500"}


def test_menos_de_tres_cotizaciones_no_se_puede_evaluar(client, tokens, SessionTest):
    f = Flujo(client, tokens)
    cid = preparar_en_cotizacion(f, plazo=12)
    f.req("PUT", f"/contrataciones/{cid}/formulario-110", "contrataciones", 200, json={
        "nro_formulario_110": "F110-2026-000458", "fecha_limite_ofertas": ahora_mas(hours=1)})
    cotizar(f, cid, "1020304050", "UNO S.R.L.", "31000", 10)
    cotizar(f, cid, "2020304050", "DOS S.R.L.", "30000", 10)
    vencer_plazo(SessionTest, cid)
    f.accion(cid, "abrir-ofertas", "contrataciones")
    r = f.accion(cid, "evaluar", "contrataciones", 422)
    assert r.json()["detail"]["codigo"] == "COTIZACIONES_INSUFICIENTES"


def test_plazo_mayor_a_15_dias_obliga_contrato(client, tokens, SessionTest):
    f = Flujo(client, tokens)
    cid = preparar_en_cotizacion(f, plazo=20)
    assert f.detalle(cid)["metodo_formalizacion"] == "CONTRATO"
    f.req("PUT", f"/contrataciones/{cid}/formulario-110", "contrataciones", 200, json={
        "nro_formulario_110": "F110-2026-000459", "fecha_limite_ofertas": ahora_mas(hours=1)})
    for nit, monto in (("1020304050", "31000"), ("2020304050", "30000"), ("3020304050", "30500")):
        cotizar(f, cid, nit, f"PROV {nit}", monto, 18)
    vencer_plazo(SessionTest, cid)
    f.accion(cid, "abrir-ofertas", "contrataciones")
    for q in f.detalle(cid)["cotizaciones"]:
        f.req("PATCH", f"/contrataciones/{cid}/cotizaciones/{q['id']}", "contrataciones", 200,
              json={"cumple_especificaciones": True})
    f.accion(cid, "evaluar", "contrataciones")
    f.accion(cid, "adjudicar", "rpa", json={})
    # una orden simple queda bloqueada
    for metodo in ("ORDEN_SERVICIO", "ORDEN_COMPRA"):
        r = f.accion(cid, "formalizar", "rpa", 422, json={"cuce": "26-1-1", "metodo_formalizacion": metodo})
        assert r.json()["detail"]["codigo"] == "FORMALIZACION_CONTRATO_OBLIGATORIO"
    c = f.accion(cid, "formalizar", "rpa", json={"cuce": "26-1-1"}).json()
    assert c["metodo_formalizacion"] == "CONTRATO"
    assert "CONTRATO_ADMINISTRATIVO" in {x["tipo_doc"] for x in c["documentos"]}
    assert "ORDEN_COMPRA_SERVICIO" not in {x["tipo_doc"] for x in c["documentos"]}
