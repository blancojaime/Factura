"""Activación: códigos firmados, equipo, vencimiento, periodo de prueba y modo solo lectura."""
import base64
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app import licencia as L

CLAVE = Path(os.environ.get("JB_CLAVE_PRIVADA", "")) if os.environ.get("JB_CLAVE_PRIVADA") else None


def emitir(priv, **d):
    datos = {"p": "JB-Personal", "e": "GAM Prueba", "m": L.id_equipo(), "i": date.today().isoformat(), "v": None}
    datos.update(d)
    raw = json.dumps(datos, separators=(",", ":")).encode()
    b = lambda x: base64.urlsafe_b64encode(x).rstrip(b"=").decode()  # noqa: E731
    return f"JBP1.{b(raw)}.{b(priv.sign(raw))}"


@pytest.fixture(autouse=True)
def restaurar_licencia(client):
    """Cada prueba empieza y termina con el estado normal de prueba (30 días), sin código."""
    def reset():
        from app.db import SessionLocal
        from app.models import Licencia
        with SessionLocal() as s:
            lic = s.get(Licencia, 1)
            if lic:
                lic.primer_uso, lic.codigo, lic.entidad, lic.vence = date.today(), "", "", None
                s.commit()
        L._cache.clear()
    reset()
    yield
    reset()


@pytest.fixture
def clave_de_pruebas(monkeypatch):
    """Par de claves SOLO de pruebas (la privada real nunca está en el repositorio)."""
    priv = Ed25519PrivateKey.generate()
    pub = base64.b64encode(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    monkeypatch.setattr(L, "CLAVE_PUBLICA_B64", pub)
    L._cache.clear()
    return priv


def test_id_equipo_estable_y_con_formato():
    a = L.id_equipo()
    assert a == L.id_equipo() and len(a) == 21 and a.startswith("JBP-")


def test_codigo_valido(clave_de_pruebas):
    d = L.verificar_codigo(emitir(clave_de_pruebas))
    assert d["e"] == "GAM Prueba"


def test_codigo_con_espacios_y_saltos_de_linea(clave_de_pruebas):
    c = emitir(clave_de_pruebas)
    assert L.verificar_codigo(c[:20] + "\n " + c[20:])


@pytest.mark.parametrize("cambio,msg", [({"m": "JBP-AAAAA-BBBBB-CCCCC"}, "OTRO equipo"),
                                        ({"v": (date.today() - timedelta(days=1)).isoformat()}, "venció"),
                                        ({"p": "Otro"}, "no es para JB-Personal")])
def test_codigos_rechazados(clave_de_pruebas, cambio, msg):
    with pytest.raises(L.LicenciaError, match=msg):
        L.verificar_codigo(emitir(clave_de_pruebas, **cambio))


def test_licencia_multiequipo_comodin(clave_de_pruebas):
    assert L.verificar_codigo(emitir(clave_de_pruebas, m="*"))


def test_firma_de_otra_clave_o_alterada(clave_de_pruebas):
    ajena = emitir(Ed25519PrivateKey.generate())
    with pytest.raises(L.LicenciaError, match="inválido o alterado"):
        L.verificar_codigo(ajena)
    c = emitir(clave_de_pruebas)
    pref, datos, firma = c.split(".")
    raw = json.loads(base64.urlsafe_b64decode(datos + "=="))
    raw["v"] = "2099-12-31"                                  # intento de extender la vigencia sin la clave privada
    nuevo = base64.urlsafe_b64encode(json.dumps(raw, separators=(",", ":")).encode()).rstrip(b"=").decode()
    with pytest.raises(L.LicenciaError):
        L.verificar_codigo(f"{pref}.{nuevo}.{firma}")
    for basura in ("", "abc", "JBP1.a.b", "JBP2.a.b"):
        with pytest.raises(L.LicenciaError):
            L.verificar_codigo(basura)


def test_clave_publica_real_incluida_y_no_acepta_otras():
    """El código de producción usa la clave pública embebida: un código firmado con otra clave no debe pasar."""
    with pytest.raises(L.LicenciaError):
        L.verificar_codigo(emitir(Ed25519PrivateKey.generate()))


def test_api_prueba_activacion_y_solo_lectura(client, clave_de_pruebas):
    from app.db import SessionLocal
    from app.models import Licencia
    e = client.get("/api/licencia").json()
    assert e["estado"] == "PRUEBA" and e["dias_restantes"] == 30 and e["id_equipo"] == L.id_equipo()
    # prueba vencida => solo lectura
    with SessionLocal() as s:
        s.get(Licencia, 1).primer_uso = date.today() - timedelta(days=31)
        s.commit()
    L._cache.clear()
    assert client.get("/api/licencia").json()["estado"] == "PRUEBA_VENCIDA"
    assert client.get("/api/empleados").status_code == 200                           # consultar: permitido
    assert client.post("/api/periodos/2026/10/procesar").status_code == 402          # escribir: bloqueado
    assert client.get("/api/reportes/2026/10/planilla.xlsx").status_code == 402      # reportes: bloqueados
    assert client.post("/api/backup", json={"password": "Respaldo-Seguro-1"}).status_code == 200   # respaldo: permitido
    # código incorrecto
    assert client.post("/api/licencia/activar", json={"codigo": "JBP1.x.y"}).status_code == 422
    assert client.post("/api/licencia/activar", json={"codigo": emitir(clave_de_pruebas, m="JBP-AAAAA-BBBBB-CCCCC")}).status_code == 422
    # activación correcta
    r = client.post("/api/licencia/activar", json={"codigo": emitir(clave_de_pruebas, e="Municipio de Prueba")})
    assert r.status_code == 200 and r.json()["estado"] == "ACTIVADA" and r.json()["entidad"] == "Municipio de Prueba"
    assert client.post("/api/periodos/2026/10/procesar").status_code == 200
    assert client.get("/api/auditoria?limite=50").json()[0]["accion"] in ("ACTIVAR_LICENCIA", "PROCESAR_PERIODO")
    # licencia con vencimiento pasado => vuelve a solo lectura
    with SessionLocal() as s:
        s.get(Licencia, 1).codigo = emitir(clave_de_pruebas, v=(date.today() - timedelta(days=2)).isoformat())
        s.commit()
    L._cache.clear()
    assert client.get("/api/licencia").json()["estado"] == "VENCIDA"
    assert client.post("/api/periodos/2026/10/procesar").status_code == 402


def test_solo_admin_activa(client, clave_de_pruebas):
    client.post("/api/usuarios", json={"username": "lector2", "password": "Lector#2026", "rol": "CONSULTA"})
    tok = client.post("/api/auth/login", json={"username": "lector2", "password": "Lector#2026"}).json()["token"]
    assert client.post("/api/licencia/activar", json={"codigo": "x"}, headers={"Authorization": f"Bearer {tok}"}).status_code == 403
