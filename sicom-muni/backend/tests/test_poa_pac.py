"""Certificacion POA (al certificar el presupuesto) y nota de solicitud de registro al PAC (compras > Bs 20.000)."""
from datetime import date

from sqlalchemy import select

from app.models import ObjetivoPOA, ParametroInstitucional
from tests.helpers import Flujo

CERT = {"preventivo_c31_nro": "C31-2026-00900"}


def _solicitada(f, objeto="Mantenimiento de equipos de oficina", partida="25800", monto="25000.00", **extra):
    c = f.crear(objeto, "SERVICIO_GENERAL", 10, **extra)
    f.item(c["id"], partida, "Servicio de mantenimiento integral", "Global", 1, monto)
    return f.accion(c["id"], "solicitar", "solicitante").json()


def tipos(c):
    return {d["tipo_doc"] for d in c["documentos"]}


def test_nota_pac_solo_para_montos_mayores_a_20000(client, tokens):
    f = Flujo(client, tokens)
    mayor = _solicitada(f, monto="25000.00", fecha_publicacion_estimada="2026-11-01")
    assert "NOTA_SOLICITUD_PAC" in tipos(mayor)
    menor = _solicitada(f, objeto="Compra de útiles menores", partida="39500", monto="18000.00")
    assert "NOTA_SOLICITUD_PAC" not in tipos(menor)
    # el limite exacto (20.000) no requiere nota: es compra directa
    exacto = _solicitada(f, objeto="Compra por el limite exacto", partida="39500", monto="20000.00")
    assert "NOTA_SOLICITUD_PAC" not in tipos(exacto)


def test_nota_pac_exige_mae_registrada(client, tokens, SessionTest):
    with SessionTest() as s:
        for clave in ("mae_nombre", "mae_cargo"):
            s.get(ParametroInstitucional, clave).valor = ""
        s.commit()
    f = Flujo(client, tokens)
    c = f.crear("Servicio sin MAE configurada", "SERVICIO_GENERAL", 10)
    f.item(c["id"], "25800", "Servicio general", "Global", 1, "30000.00")
    r = f.accion(c["id"], "solicitar", "solicitante", 422)
    assert any("Máxima Autoridad Ejecutiva" in e for e in r.json()["detail"]["errores"])
    # una compra directa no necesita MAE
    d = f.crear("Compra directa sin MAE", "SERVICIO_GENERAL", 10)
    f.item(d["id"], "25800", "Servicio general", "Global", 1, "1000.00")
    f.accion(d["id"], "solicitar", "solicitante", 200)


def test_certificacion_poa_al_certificar(client, tokens, SessionTest):
    f = Flujo(client, tokens)
    c = _solicitada(f)
    cid = c["id"]
    assert "CERTIFICACION_POA" not in tipos(c)
    # el panel de presupuesto consulta programa -> objetivo
    prog = f.req("GET", f"/contrataciones/{cid}/poa", "presupuesto", 200).json()
    assert len(prog) == 1 and prog[0]["programa"] == "01" and prog[0]["objetivo_registrado"] and prog[0]["codigo_objetivo"] == "OBJ2"
    # sin justificacion no se certifica
    with SessionTest() as s:
        from app.models import ContratacionMenor
        import uuid
        s.get(ContratacionMenor, uuid.UUID(cid)).justificacion_poa = ""
        s.commit()
    r = f.accion(cid, "certificar", "presupuesto", 422, json=CERT)
    assert r.json()["detail"]["codigo"] == "POA_INCOMPLETO" and any("Justifique" in e for e in r.json()["detail"]["errores"])
    # con justificacion (la registra Presupuesto al certificar)
    c = f.accion(cid, "certificar", "presupuesto", json={**CERT, "justificacion_poa": "La compra mantiene operativos los equipos que sostienen la gestión administrativa."}).json()
    assert c["estado"] == "CERTIFICADO_PRESUPUESTO" and "CERTIFICACION_POA" in tipos(c)
    assert c["justificacion_poa"].startswith("La compra mantiene")


def test_certificacion_poa_exige_objetivo_del_programa(client, tokens, SessionTest):
    with SessionTest() as s:
        o = s.scalar(select(ObjetivoPOA).where(ObjetivoPOA.programa == "1"))
        s.delete(o)
        s.commit()
    f = Flujo(client, tokens)
    c = _solicitada(f)
    r = f.accion(c["id"], "certificar", "presupuesto", 422, json=CERT)
    assert r.json()["detail"]["codigo"] == "POA_INCOMPLETO"
    assert any("no tiene objetivo del POA" in e for e in r.json()["detail"]["errores"])
    # el saldo no se toco (todo o nada)
    assert f.partida("25800")["saldo_disponible"] in ("45000.00", "45000")
    # al registrar el objetivo se puede certificar
    f.req("PUT", "/poa/objetivos", "presupuesto", 200, json={"gestion": date.today().year, "programa": "01", "codigo_objetivo": "OBJ-A",
          "descripcion_objetivo": "Objetivo registrado manualmente", "denominacion_programa": "PROGRAMA 1"})
    assert f.accion(c["id"], "certificar", "presupuesto", json=CERT).json()["estado"] == "CERTIFICADO_PRESUPUESTO"
