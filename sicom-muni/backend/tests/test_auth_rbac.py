"""Autenticacion JWT, refresh en cookie HTTP-only, bloqueo por intentos y control de acceso por rol."""
import pytest

from app import seeds
from tests.helpers import API, Flujo

LOGIN = f"{API}/auth/login"


def login(client, u="solicitante", p=seeds.PASSWORD_DEMO):
    return client.post(LOGIN, json={"username": u, "password": p})


def test_login_ok_y_cookie_httponly(client):
    r = login(client)
    assert r.status_code == 200 and r.json()["expires_in"] == 900
    set_cookie = r.headers["set-cookie"].lower()
    assert "refresh_token=" in set_cookie and "httponly" in set_cookie and "samesite=strict" in set_cookie
    assert "refresh_token" not in r.json()  # el refresh jamas viaja en el cuerpo
    me = client.get(f"{API}/auth/me", headers={"Authorization": "Bearer " + r.json()["access_token"]})
    assert me.json()["rol"] == "ROL_SOLICITANTE"


def test_password_y_usuario_incorrectos_mismo_mensaje(client):
    a, b = login(client, p="Incorrecta#1"), login(client, u="noexiste")
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_bloqueo_tras_5_intentos(client):
    for _ in range(5):
        assert login(client, p="mala").status_code == 401
    r = login(client)  # aun con la clave correcta
    assert r.status_code == 423


def test_refresh_rota_y_detecta_reutilizacion(client):
    r = login(client)
    viejo = client.cookies.get("refresh_token")
    r2 = client.post(f"{API}/auth/refresh")
    assert r2.status_code == 200 and client.cookies.get("refresh_token") != viejo
    # reutilizar el refresh anterior revoca toda la familia
    client.cookies.set("refresh_token", viejo, path="/api/v1/auth")
    assert client.post(f"{API}/auth/refresh").status_code == 401
    assert client.post(f"{API}/auth/refresh").status_code == 401


def test_logout_revoca_refresh(client):
    login(client)
    token = client.cookies.get("refresh_token")
    assert client.post(f"{API}/auth/logout").status_code == 204
    client.cookies.set("refresh_token", token, path="/api/v1/auth")
    assert client.post(f"{API}/auth/refresh").status_code == 401


def test_sin_token_o_token_invalido(client):
    assert client.get(f"{API}/contrataciones").status_code == 401
    assert client.get(f"{API}/contrataciones", headers={"Authorization": "Bearer xxx"}).status_code == 401
    # un refresh token no sirve como access token
    login(client)
    assert client.get(f"{API}/contrataciones", headers={"Authorization": "Bearer " + client.cookies.get("refresh_token")}).status_code == 401


# ---------------- RBAC
def test_cada_rol_solo_ejecuta_sus_acciones(client, tokens):
    f = Flujo(client, tokens)
    c = f.crear("Compra de útiles de escritorio para la gestión", "BIEN", 5)
    cid = c["id"]
    # solo el solicitante crea; los demas roles reciben 403
    for rol in ("presupuesto", "contrataciones", "rpa", "recepcion", "admin"):
        f.req("POST", "/contrataciones", rol, 403, json={
            "objeto_contratacion": "Intento no autorizado", "tipo_objeto": "BIEN", "plazo_dias_calendario": 5})
    # acciones del flujo con el rol equivocado
    for accion, rol in (("certificar", "solicitante"), ("certificar", "rpa"), ("aprobar-inicio", "presupuesto"),
                        ("evaluar", "rpa"), ("adjudicar", "contrataciones"), ("formalizar", "presupuesto"),
                        ("recepcion", "rpa"), ("devengar", "contrataciones"), ("abrir-ofertas", "rpa")):
        body = {"fecha_recepcion": "2026-01-01", "conforme": True} if accion == "recepcion" else {}
        f.req("POST", f"/contrataciones/{cid}/{accion}", rol, 403, json=body)
    # administracion: solo ADMIN
    f.req("GET", "/admin/usuarios", "rpa", 403)
    f.req("GET", "/admin/auditoria", "presupuesto", 403)
    f.req("PUT", "/admin/parametros/nombre_gam", "contrataciones", 403, json={"valor": "X"})
    f.req("POST", "/catalogo-chb", "solicitante", 403, json={"codigo_unspsc": "12345678", "descripcion_bien": "Prueba"})


def test_solicitante_solo_ve_sus_tramites(client, tokens, SessionTest, hash_demo):
    f = Flujo(client, tokens)
    cid = f.crear("Tramite del solicitante uno", "BIEN", 5)["id"]
    # otro solicitante
    f.req("POST", "/admin/usuarios", "admin", 201, json={
        "username": "solicitante2", "password": "Otra#Clave2026", "nombre_completo": "Otro Solicitante", "rol": "ROL_SOLICITANTE"})
    h2 = {"Authorization": "Bearer " + login(client, "solicitante2", "Otra#Clave2026").json()["access_token"]}
    assert client.get(f"{API}/contrataciones", headers=h2).json() == []
    assert client.get(f"{API}/contrataciones/{cid}", headers=h2).status_code == 404  # no se revela la existencia
    assert client.post(f"{API}/contrataciones/{cid}/anular", headers=h2, json={"motivo": "Intento ajeno de anular"}).status_code == 404
    # el resto de roles si ve todo
    assert len(f.req("GET", "/contrataciones", "rpa", 200).json()) == 1


def test_politica_de_contrasenas_y_usuarios(client, tokens):
    f = Flujo(client, tokens)
    r = f.req("POST", "/admin/usuarios", "admin", 422, json={"username": "nuevo1", "password": "corta1A", "nombre_completo": "Nuevo Usuario", "rol": "ROL_RPA"})
    assert "10 caracteres" in r.json()["detail"]
    f.req("POST", "/admin/usuarios", "admin", 201, json={"username": "nuevo1", "password": "ClaveSegura2026", "nombre_completo": "Nuevo Usuario", "rol": "ROL_RPA"})
    f.req("POST", "/admin/usuarios", "admin", 409, json={"username": "nuevo1", "password": "ClaveSegura2026", "nombre_completo": "Nuevo Usuario", "rol": "ROL_RPA"})
    # un administrador no puede degradarse ni desactivarse
    uid = next(u["id"] for u in f.req("GET", "/admin/usuarios", "admin", 200).json() if u["username"] == "admin")
    f.req("PATCH", f"/admin/usuarios/{uid}", "admin", 422, json={"activo": False})
    f.req("PATCH", f"/admin/usuarios/{uid}", "admin", 422, json={"rol": "ROL_RPA"})
    # el hash guardado es Argon2id
    from sqlalchemy import select
    from app.models import Usuario
    assert Usuario  # noqa


def test_hash_argon2(db):
    from sqlalchemy import select
    from app.models import Usuario
    h = db.scalar(select(Usuario.password_hash).where(Usuario.username == "admin"))
    assert h.startswith("$argon2id$") and seeds.PASSWORD_DEMO not in h
