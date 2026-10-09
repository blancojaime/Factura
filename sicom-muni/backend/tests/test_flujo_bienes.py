"""CASO 1 (E2E): compra de BIENES — material de construccion por Bs 18.500.

Cuantia <= Bs 20.000 (compra directa, sin Formulario 110), plazo 10 dias (Orden de Compra) y excepcion CHB
para cemento y ladrillo (existen en el catalogo) y arena/piedra (sin coincidencia).
"""
from decimal import Decimal

from sqlalchemy import select

from app.models import PartidaPresupuestaria
from tests.helpers import Flujo

JUSTIFICACION_CHB = ("Los proveedores del catálogo CHB no pueden entregar los materiales en el plazo de obra de 10 días ni "
                     "en la cantidad requerida por la unidad; se fundamenta la compra directa en el mercado local.")


def test_caso1_material_de_construccion_18500(client, tokens, SessionTest):
    f = Flujo(client, tokens)
    c = f.crear("Adquisición de material de construcción para mantenimiento de la plaza principal", "BIEN", 10)
    cid = c["id"]
    assert c["correlativo_interno"].startswith("CM-") and c["estado"] == "BORRADOR"

    # --- items: consulta obligatoria al catalogo CHB
    r_cem = f.item(cid, "34200", "Cemento portland IP-30 bolsa de 50 kg", "Bolsa", 120, "62.00", codigo="30111505").json()
    assert next(i for i in r_cem["items"] if i["codigo_unspsc"] == "30111505")["estado_chb"] == "COMPRA_CHB_OBLIGATORIA"
    f.item(cid, "34200", "Ladrillo cerámico de 6 huecos", "Unidad", 3950, "1.30", codigo="30131501")
    f.item(cid, "34200", "Arena fina lavada", "m3", 30, "85.00", codigo="11111501")
    d = f.item(cid, "34200", "Piedra chancada de 3/4 pulgada", "m3", 25, "135.00", codigo="11111503").json()
    assert Decimal(d["monto_referencial_total"]) == Decimal("18500.00")
    assert d["modalidad_cuantia"] == "COMPRA_DIRECTA" and d["metodo_formalizacion"] == "ORDEN_COMPRA"
    estados = {i["codigo_unspsc"]: i["estado_chb"] for i in d["items"]}
    assert estados["11111501"] == "SIN_COINCIDENCIA" and estados["30131501"] == "COMPRA_CHB_OBLIGATORIA"

    # --- no puede solicitar: cemento y ladrillo deben comprarse por catalogo o justificarse
    r = f.accion(cid, "solicitar", "solicitante", 422)
    errores = r.json()["detail"]["errores"]
    assert any("Compro Hecho en Bolivia" in e and "30111505" in e for e in errores)
    assert any("justificación" in e.lower() for e in errores)

    # --- el solicitante fundamenta la excepcion (los dos ítems del catalogo pasan a "fuera de catalogo")
    for it in d["items"]:
        if it["codigo_unspsc"] in ("30111505", "30131501"):
            f.req("PUT", f"/contrataciones/{cid}/items/{it['id']}", "solicitante", 200, json={
                "codigo_unspsc": it["codigo_unspsc"], "partida_id": it["partida_id"],
                "descripcion_especifica": it["descripcion_especifica"], "unidad_medida": it["unidad_medida"],
                "cantidad": it["cantidad"], "precio_unitario_ref": it["precio_unitario_ref"], "fuera_catalogo_chb": True})
    f.req("PATCH", f"/contrataciones/{cid}", "solicitante", 200, json={
        "justificacion_excepcion_chb": JUSTIFICACION_CHB, "codigo_autorizacion_chb": "MDPyEP-AUT-0391"})
    c = f.accion(cid, "solicitar", "solicitante").json()
    assert c["estado"] == "SOLICITADO" and c["requiere_excepcion_chb"] is True
    tipos = {x["tipo_doc"] for x in c["documentos"]}
    assert {"C1_SOLICITUD", "INFORME_EXCEPCION_CHB"} <= tipos

    # --- presupuesto: bloque SIGEP previsto, certificacion y descuento del saldo
    prev = f.req("GET", f"/contrataciones/{cid}/bloque-sigep", "presupuesto", 200).json()
    assert prev["origen"] == "PREVISTO" and prev["total"] == "18500.00"
    c = f.accion(cid, "certificar", "presupuesto", json={"preventivo_c31_nro": "C31-2026-00123"}).json()
    assert c["estado"] == "CERTIFICADO_PRESUPUESTO" and c["preventivo_c31_nro"] == "C31-2026-00123"
    blq = f.req("GET", f"/contrataciones/{cid}/bloque-sigep", "presupuesto", 200).json()
    assert blq["origen"] == "PREVENTIVO"
    assert blq["texto_pipe"] == "01 | 001 | 01 | 0000 | 001 | 20 | 230 | 34200 | 18500.00"
    assert f.partida("34200")["saldo_disponible"] in ("61500.00", "61500")

    # --- RPA aprueba el inicio; compra directa: no se exige Formulario 110
    c = f.accion(cid, "aprobar-inicio", "rpa").json()
    assert c["estado"] == "EN_COTIZACION" and c["modalidad_cuantia"] == "COMPRA_DIRECTA"

    # --- cotizaciones selladas (monto cifrado) -> apertura -> calificacion -> matriz
    qa = f.req("POST", f"/contrataciones/{cid}/cotizaciones", "contrataciones", 201, json={
        "nit_ci": "1023456028", "razon_social": "FERRETERIA EL CONSTRUCTOR S.R.L.", "monto_total_ofertado": "18200.00",
        "plazo_ofertado_dias": 8}).json()
    qb = f.req("POST", f"/contrataciones/{cid}/cotizaciones", "contrataciones", 201, json={
        "nit_ci": "4012345011", "razon_social": "MATERIALES BOLIVIA LTDA.", "monto_total_ofertado": "17900.00",
        "plazo_ofertado_dias": 10}).json()
    assert qa["sellada"] and qa["monto_total_ofertado"] is None
    f.req("POST", f"/contrataciones/{cid}/cotizaciones", "contrataciones", 422, json={  # NIT duplicado
        "nit_ci": "4012345011", "razon_social": "OTRA", "monto_total_ofertado": "100", "plazo_ofertado_dias": 5})
    f.req("GET", f"/contrataciones/{cid}/evaluacion", "contrataciones", 422)  # selladas: no hay matriz
    c = f.accion(cid, "abrir-ofertas", "contrataciones").json()
    assert c["ofertas_abiertas"] is True
    for q in c["cotizaciones"]:
        f.req("PATCH", f"/contrataciones/{cid}/cotizaciones/{q['id']}", "contrataciones", 200,
              json={"cumple_especificaciones": True})
    m = f.req("GET", f"/contrataciones/{cid}/evaluacion", "contrataciones", 200).json()
    assert m["recomendada"] == qb["id"] and [o["ranking"] for o in m["ofertas"]] == [1, 2]
    c = f.accion(cid, "evaluar", "contrataciones").json()
    assert c["estado"] == "EVALUADO" and "CUADRO_COMPARATIVO" in {x["tipo_doc"] for x in c["documentos"]}

    # --- adjudicacion
    c = f.accion(cid, "adjudicar", "rpa", json={}).json()
    assert c["estado"] == "ADJUDICADO" and any(q["adjudicado"] and q["id"] == qb["id"] for q in c["cotizaciones"])

    # --- formalizacion: plazo 10 dias => ORDEN DE COMPRA (no se acepta un contrato ni otro metodo)
    f.accion(cid, "formalizar", "rpa", 422, json={"metodo_formalizacion": "CONTRATO"})
    c = f.accion(cid, "formalizar", "rpa", json={}).json()
    assert c["estado"] == "FORMALIZADO" and c["metodo_formalizacion"] == "ORDEN_COMPRA"
    assert "ORDEN_COMPRA_SERVICIO" in {x["tipo_doc"] for x in c["documentos"]}

    # --- recepcion: primero observada (faltante), luego conforme
    detalle = [{"numero": i["numero"], "cantidad_recibida": i["cantidad"], "conforme": True} for i in c["items"]]
    detalle[0]["cantidad_recibida"] = "100"
    hoy = __import__("datetime").date.today().isoformat()
    f.accion(cid, "recepcion", "recepcion", 422, json={"fecha_recepcion": hoy, "conforme": True, "detalle": detalle})
    c = f.accion(cid, "recepcion", "recepcion", json={
        "fecha_recepcion": hoy, "conforme": False, "observaciones": "Faltan 20 bolsas de cemento por entregar",
        "detalle": detalle}).json()
    assert c["estado"] == "FORMALIZADO" and len(c["recepciones"]) == 1 and not c["recepciones"][0]["conforme"]
    c = f.accion(cid, "recepcion", "recepcion", json={"fecha_recepcion": hoy, "conforme": True}).json()
    assert c["estado"] == "RECEPCIONADO" and c["recepciones"][-1]["nro_nia"].startswith("NIA-")
    assert "ACTA_RECEPCION_FORM500" in {x["tipo_doc"] for x in c["documentos"]}

    # --- devengado: libera la diferencia entre lo reservado (18.500) y lo adjudicado (17.900)
    c = f.accion(cid, "devengar", "presupuesto").json()
    assert c["estado"] == "DEVENGADO"
    assert Decimal(f.partida("34200")["saldo_disponible"]) == Decimal("62100.00")
    assert {p["estado"] for p in c["preventivos"]} == {"DEVENGADO"} and Decimal(c["preventivos"][0]["importe"]) == Decimal("17900.00")

    # --- expediente completo y auditoria integra
    tipos = {x["tipo_doc"] for x in c["documentos"]}
    assert tipos == {"C1_SOLICITUD", "INFORME_EXCEPCION_CHB", "CERTIFICACION_C31", "CUADRO_COMPARATIVO",
                     "NOTA_ADJUDICACION", "ORDEN_COMPRA_SERVICIO", "ACTA_RECEPCION_FORM500"}
    v = f.req("GET", "/admin/auditoria/verificar", "admin", 200).json()
    assert v["ok"] is True and v["total"] > 20
