"""Bloqueos normativos y casos de borde: limite de Bs 50.000, saldo insuficiente, anulacion, desierto, sobres sellados."""
from decimal import Decimal

from tests.helpers import Flujo
from tests.test_flujo_servicio import cotizar, preparar_en_cotizacion, vencer_plazo


def test_monto_mayor_a_50000_bloquea_con_mensaje_anpe(client, tokens):
    f = Flujo(client, tokens)
    cid = f.crear("Equipamiento mayor del taller municipal", "BIEN", 10)["id"]
    f.item(cid, "43100", "Escritorio ejecutivo", "Unidad", 40, "1000.00", codigo="56101500", fuera=True)  # 40.000 ok
    r = f.item(cid, "43100", "Sillón gerencial", "Unidad", 10, "1000.01", codigo="56101500", fuera=True, esperado=422)  # supera 50.000 por 0.10
    d = r.json()["detail"]
    assert d["codigo"] == "SUPERA_CONTRATACION_MENOR"
    assert d["mensaje"] == "El monto supera el límite de Contratación Menor (Bs 50.000). Derive a la modalidad ANPE"
    # exactamente 50.000 si es valido
    r = f.item(cid, "43100", "Sillón gerencial", "Unidad", 10, "1000.00", codigo="56101500", fuera=True)
    assert Decimal(r.json()["monto_referencial_total"]) == Decimal("50000.00")
    assert r.json()["modalidad_cuantia"] == "CONSULTA_PRECIOS_SICOES"


def test_monto_tope_20000_exacto_es_compra_directa(client, tokens):
    f = Flujo(client, tokens)
    cid = f.crear("Útiles de escritorio por el tope de compra directa", "BIEN", 5)["id"]
    r = f.item(cid, "39500", "Útiles de escritorio varios", "Global", 1, "20000.00", codigo="44121600", fuera=True).json()
    assert r["modalidad_cuantia"] == "COMPRA_DIRECTA"
    r = f.item(cid, "39500", "Un ítem adicional", "Unidad", 1, "0.01", codigo="44121601", fuera=True).json()
    assert r["modalidad_cuantia"] == "CONSULTA_PRECIOS_SICOES"


def test_bien_exige_codigo_unspsc(client, tokens):
    f = Flujo(client, tokens)
    cid = f.crear("Compra sin código UNSPSC", "BIEN", 5)["id"]
    r = f.item(cid, "39500", "Resmas de papel", "Resma", 10, "30.00", codigo="", esperado=422)
    assert r.json()["detail"]["codigo"] == "CHB_CODIGO_OBLIGATORIO"


def test_saldo_insuficiente_y_devolucion(client, tokens):
    f = Flujo(client, tokens)
    cid = f.crear("Equipos de oficina por encima del saldo", "BIEN", 10)["id"]
    f.item(cid, "39500", "Impresoras multifuncionales", "Unidad", 10, "3500.00", codigo="43211500", fuera=True)  # 35.000 > saldo 30.000
    f.req("PATCH", f"/contrataciones/{cid}", "solicitante", 200, json={
        "justificacion_excepcion_chb": "Las impresoras requeridas no existen en el catálogo con las características técnicas "
                                       "exigidas por la unidad y se necesitan de forma inmediata."})
    f.accion(cid, "solicitar", "solicitante")
    r = f.accion(cid, "certificar", "presupuesto", 422, json={})
    d = r.json()["detail"]
    assert d["codigo"] == "SALDO_INSUFICIENTE" and "39500" in d["errores"][0]
    assert f.partida("39500")["saldo_disponible"] in ("30000.00", "30000")  # no se descuenta nada
    c = f.accion(cid, "devolver", "presupuesto", json={"motivo": "Saldo insuficiente en la partida 39500"}).json()
    assert c["estado"] == "BORRADOR" and "Saldo insuficiente" in c["ultima_observacion"]


def test_anular_libera_el_saldo(client, tokens):
    f = Flujo(client, tokens)
    cid = preparar_en_cotizacion(f, plazo=12)
    assert Decimal(f.partida("25800")["saldo_disponible"]) == Decimal("13000.00")
    f.accion(cid, "anular", "solicitante", 403, json={"motivo": "El solicitante ya no puede anular aquí"})  # ya certificado
    c = f.accion(cid, "anular", "rpa", json={"motivo": "Cambio de prioridades institucionales"}).json()
    assert c["estado"] == "ANULADO" and c["motivo_cierre"].startswith("ANULADO")
    assert Decimal(f.partida("25800")["saldo_disponible"]) == Decimal("45000.00")
    assert {p["estado"] for p in c["preventivos"]} == {"LIBERADO"}
    f.accion(cid, "aprobar-inicio", "rpa", 409)  # un tramite anulado no avanza


def test_solicitante_puede_anular_antes_de_certificar(client, tokens):
    f = Flujo(client, tokens)
    cid = f.crear("Tramite que se cancela", "SERVICIO_GENERAL", 5)["id"]
    c = f.accion(cid, "anular", "solicitante", json={"motivo": "Ya no se requiere la contratación"}).json()
    assert c["estado"] == "ANULADO"


def test_declarar_desierto_libera_saldo(client, tokens, SessionTest):
    f = Flujo(client, tokens)
    cid = preparar_en_cotizacion(f, plazo=12)
    f.req("PUT", f"/contrataciones/{cid}/formulario-110", "contrataciones", 200, json={
        "nro_formulario_110": "F110-2026-000460", "fecha_limite_ofertas": "2030-01-01T00:00:00+00:00"})
    for nit in ("1020304050", "2020304050", "3020304050"):
        cotizar(f, cid, nit, f"PROV {nit}", "31000", 10)
    vencer_plazo(SessionTest, cid)
    f.accion(cid, "abrir-ofertas", "contrataciones")
    for q in f.detalle(cid)["cotizaciones"]:  # ninguna cumple
        f.req("PATCH", f"/contrataciones/{cid}/cotizaciones/{q['id']}", "contrataciones", 200, json={"cumple_especificaciones": False})
    assert f.accion(cid, "evaluar", "contrataciones", 422).json()["detail"]["codigo"] == "SIN_ELEGIBLES"
    c = f.accion(cid, "declarar-desierta", "rpa", json={"motivo": "Ninguna oferta cumple las especificaciones"}).json()
    assert c["estado"] == "ANULADO" and c["motivo_cierre"].startswith("DESIERTO")
    assert Decimal(f.partida("25800")["saldo_disponible"]) == Decimal("45000.00")


def test_ofertas_selladas_hasta_la_apertura(client, tokens, SessionTest):
    f = Flujo(client, tokens)
    cid = preparar_en_cotizacion(f, plazo=12)
    f.req("PUT", f"/contrataciones/{cid}/formulario-110", "contrataciones", 200, json={
        "nro_formulario_110": "F110-2026-000461", "fecha_limite_ofertas": "2030-01-01T00:00:00+00:00"})
    cotizar(f, cid, "1020304050", "PROV UNO", "31000", 10)
    for rol in ("rpa", "presupuesto", "contrataciones", "admin"):
        c = f.detalle(cid, rol)
        assert c["cotizaciones"][0]["monto_total_ofertado"] is None and c["cotizaciones"][0]["sellada"] is True
    # el monto no esta en texto claro en la base de datos
    from sqlalchemy import text
    with SessionTest() as s:
        fila = s.execute(text("SELECT monto_total_ofertado, monto_cifrado FROM cotizaciones_proveedores")).one()
        assert fila[0] is None and fila[1] is not None and b"31000" not in bytes(fila[1])
    # no se puede registrar una oferta recibida despues del plazo / en el futuro
    r = f.req("POST", f"/contrataciones/{cid}/cotizaciones", "contrataciones", 422, json={
        "nit_ci": "9999999", "razon_social": "FUTURA", "monto_total_ofertado": "100", "plazo_ofertado_dias": 5,
        "fecha_recepcion": "2099-01-01T00:00:00+00:00"})
    assert r.json()["detail"]["codigo"] in ("RECEPCION_FUTURA", "OFERTA_EXTEMPORANEA")


def test_estados_invalidos(client, tokens):
    f = Flujo(client, tokens)
    cid = f.crear("Tramite en borrador", "BIEN", 5)["id"]
    for accion, rol in (("certificar", "presupuesto"), ("aprobar-inicio", "rpa"), ("devengar", "presupuesto")):
        f.accion(cid, accion, rol, 409, json={})
    f.accion(cid, "solicitar", "solicitante", 422)  # sin items ni especificaciones suficientes
    # tras solicitar ya no se edita
    cid2 = f.crear("Servicio de limpieza de oficinas", "SERVICIO_GENERAL", 5)["id"]
    f.item(cid2, "25800", "Limpieza integral", "Global", 1, "1500.00")
    f.accion(cid2, "solicitar", "solicitante")
    f.item(cid2, "25800", "Otro", "Global", 1, "100.00", esperado=409)
    f.req("PATCH", f"/contrataciones/{cid2}", "solicitante", 409, json={"objeto_contratacion": "Cambio posterior a la solicitud"})
