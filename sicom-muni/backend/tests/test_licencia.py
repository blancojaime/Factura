"""Licencias: firma Ed25519 ligada al equipo, modo de prueba, activacion, limite de usuarios y servicio de la pantalla web."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import seeds
from app.config import get_settings
from app.main import crear_app
from app.models import ParametroInstitucional
from app.services import licencia, licencia_core as core

EQUIPO = core.id_equipo()


@pytest.fixture()
def llaves(tmp_path):
    priv, pub = core.generar_par_llaves()
    ruta = tmp_path / "pub.pem"
    ruta.write_bytes(pub)
    return priv, pub, str(ruta)


@pytest.fixture()
def obligatoria(llaves, monkeypatch, SessionTest):
    s = get_settings()
    monkeypatch.setattr(s, "licencia_obligatoria", True)
    monkeypatch.setattr(s, "licencia_llave_publica", llaves[2])
    monkeypatch.setattr(licencia, "SessionLocal", SessionTest)
    licencia.invalidar_cache()
    return llaves


# ------------------------------------------------------------------ nucleo
def test_id_equipo_estable_y_con_formato():
    assert EQUIPO == core.id_equipo() and len(EQUIPO) == 19 and EQUIPO.count("-") == 3


def test_emitir_y_verificar(llaves):
    priv, pub, _ = llaves
    lic = core.emitir(priv, entidad="GAM de Prueba", equipo=EQUIPO, vence=date.today() + timedelta(days=30), max_usuarios=5)
    r = core.verificar(lic, pub, EQUIPO)
    assert r.valida and r.datos["entidad"] == "GAM de Prueba" and r.dias_restantes == 30
    clave = core.a_clave(lic)
    assert clave.startswith("SICOM1-") and core.verificar(clave, pub, EQUIPO).valida  # clave de una linea
    assert core.verificar(core.leer(clave), pub, core.normalizar_id(EQUIPO.replace("-", "").lower())).valida


def test_firma_alterada_equipo_ajeno_y_vencida(llaves):
    priv, pub, _ = llaves
    lic = core.emitir(priv, entidad="GAM", equipo=EQUIPO)
    lic["datos"]["entidad"] = "OTRA ENTIDAD"
    assert core.verificar(lic, pub, EQUIPO).codigo == "FIRMA"
    otra_pub = core.generar_par_llaves()[1]
    assert core.verificar(core.emitir(priv, entidad="GAM", equipo=EQUIPO), otra_pub, EQUIPO).codigo == "FIRMA"
    assert core.verificar(core.emitir(priv, entidad="GAM", equipo="AAAA-BBBB-CCCC-DDDD"), pub, EQUIPO).codigo == "EQUIPO"
    vencida = core.emitir(priv, entidad="GAM", equipo=EQUIPO, vence=date.today() - timedelta(days=1))
    assert core.verificar(vencida, pub, EQUIPO).codigo == "VENCIDA"
    assert core.verificar(core.emitir(priv, entidad="GAM"), pub, EQUIPO).valida  # "*": cualquier equipo
    assert core.verificar("no es una licencia", pub, EQUIPO).codigo == "FORMATO"
    with pytest.raises(ValueError):
        core.emitir(priv, entidad="GAM", equipo="1234")


def test_llave_publica_del_repositorio_es_valida():
    assert core.cargar_publica(licencia.llave_publica())


# ------------------------------------------------------------------ servidor
def test_sin_licencia_obligatoria_todo_funciona(client):
    e = client.get("/api/v1/licencia").json()
    assert e["modo"] == "NO_REQUERIDA" and e["operativo"] is True and e["id_equipo"] == EQUIPO


def test_prueba_activacion_y_bloqueo(client, tokens, obligatoria, SessionTest):
    priv, _, _ = obligatoria
    e = client.get("/api/v1/licencia").json()
    assert e["modo"] == "PRUEBA" and e["dias_restantes"] == 30 and e["operativo"]
    assert client.get("/api/v1/partidas", headers=tokens["solicitante"]).status_code == 200
    # termina la prueba: la API (salvo licencia y salud) responde 402
    with SessionTest() as s:
        s.get(ParametroInstitucional, "prueba_inicio").valor = (date.today() - timedelta(days=45)).isoformat()
        s.commit()
    licencia.invalidar_cache()
    r = client.get("/api/v1/partidas", headers=tokens["solicitante"])
    assert r.status_code == 402 and r.json()["detail"]["codigo"] == "LICENCIA_REQUERIDA"
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": seeds.PASSWORD_DEMO}).status_code == 402
    assert client.get("/api/v1/licencia").json()["modo"] == "PRUEBA_VENCIDA"
    # una licencia de otro equipo o falsa se rechaza
    mala = core.a_clave(core.emitir(priv, entidad="GAM", equipo="AAAA-BBBB-CCCC-DDDD"))
    assert client.post("/api/v1/licencia", json={"texto": mala}).status_code == 422
    assert client.post("/api/v1/licencia", json={"texto": "SICOM1-" + "A" * 40}).status_code == 422
    # la licencia correcta reactiva el sistema
    buena = core.a_clave(core.emitir(priv, entidad="GAM de Prueba", equipo=EQUIPO, vence=date.today() + timedelta(days=365)))
    e = client.post("/api/v1/licencia", json={"texto": buena}).json()
    assert e["modo"] == "LICENCIADA" and e["entidad"] == "GAM de Prueba" and e["operativo"]
    assert client.get("/api/v1/partidas", headers=tokens["solicitante"]).status_code == 200


def test_limite_de_usuarios(client, tokens, obligatoria):
    priv, _, _ = obligatoria
    corta = core.a_clave(core.emitir(priv, entidad="GAM", equipo=EQUIPO, max_usuarios=3))
    r = client.post("/api/v1/licencia", json={"texto": corta})
    assert r.status_code == 422 and "usuario" in r.json()["detail"]  # hay 6 usuarios activos
    activa = core.a_clave(core.emitir(priv, entidad="GAM", equipo=EQUIPO, max_usuarios=7))
    assert client.post("/api/v1/licencia", json={"texto": activa}).status_code == 200
    nuevo = {"username": "nuevo1", "password": "Clave#Segura2026", "nombre_completo": "Usuario Nuevo", "cargo": "X", "rol": "ROL_SOLICITANTE", "email": ""}
    assert client.post("/api/v1/admin/usuarios", headers=tokens["admin"], json=nuevo).status_code == 201
    r = client.post("/api/v1/admin/usuarios", headers=tokens["admin"], json={**nuevo, "username": "nuevo2"})
    assert r.status_code == 422 and "7" in r.json()["detail"]


# ------------------------------------------------------------------ pantalla web
def test_servicio_de_la_pantalla_web(tmp_path, monkeypatch):
    web = tmp_path / "web"
    (web / "contrataciones" / "_").mkdir(parents=True)
    (web / "contrataciones" / "nueva").mkdir()
    (web / "verificar" / "_").mkdir(parents=True)
    (web / "_next" / "static").mkdir(parents=True)
    (web / "index.html").write_text("INICIO")
    (web / "contrataciones" / "index.html").write_text("LISTA")
    (web / "contrataciones" / "_" / "index.html").write_text("DETALLE")
    (web / "contrataciones" / "nueva" / "index.html").write_text("NUEVA")
    (web / "verificar" / "_" / "index.html").write_text("VERIFICAR")
    (web / "_next" / "static" / "app.js").write_text("js")
    (web / "404.html").write_text("NO EXISTE")
    monkeypatch.setattr(get_settings(), "static_dir", str(web))
    c = TestClient(crear_app())
    assert c.get("/").text == "INICIO"
    assert c.get("/contrataciones/").text == "LISTA" and c.get("/contrataciones").text == "LISTA"
    assert c.get("/contrataciones/nueva/").text == "NUEVA"
    assert c.get("/contrataciones/3f2c9f6e-1111-4222-8333-444455556666/").text == "DETALLE"
    assert c.get("/verificar/abc-123").text == "VERIFICAR"
    js = c.get("/_next/static/app.js")
    assert js.text == "js" and "immutable" in js.headers["cache-control"]
    assert c.get("/no-existe").status_code == 404 and c.get("/no-existe").text == "NO EXISTE"
    assert c.get("/../../etc/passwd").status_code in (404, 400)
    assert c.get("/api/v1/inexistente").status_code == 404 and c.get("/api/v1/inexistente").headers["content-type"].startswith("application/json")
