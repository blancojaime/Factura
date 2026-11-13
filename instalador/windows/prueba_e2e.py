#!/usr/bin/env python3
"""Prueba de punta a punta de un SICOM-MUNI instalado (solo biblioteca estándar).

Uso: prueba_e2e.py URL USUARIO_ADMIN CLAVE_ADMIN
Recorre: pantalla web, licencia, usuarios por rol, presupuesto, POA, solicitud > Bs 20.000 (nota PAC), certificación,
descarga de PDF con QR y verificación pública del archivo, y la cadena de auditoría.
"""
import json
import sys
import uuid
import urllib.error
import urllib.request
from datetime import date

BASE = sys.argv[1].rstrip("/")
ADMIN, CLAVE_ADMIN = sys.argv[2], sys.argv[3]
SUF = uuid.uuid4().hex[:6]
CLAVE = "Prueba#Segura2026"
fallos: list[str] = []


def llamar(metodo, ruta, token=None, datos=None, crudo=False, multipart=None, esperado=(200, 201)):
    cabeceras = {"Accept": "application/json"}
    cuerpo = None
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    if datos is not None:
        cuerpo = json.dumps(datos).encode()
        cabeceras["Content-Type"] = "application/json"
    if multipart is not None:
        limite = uuid.uuid4().hex
        cabeceras["Content-Type"] = f"multipart/form-data; boundary={limite}"
        cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"archivo\"; filename=\"doc.pdf\"\r\n"
                  f"Content-Type: application/pdf\r\n\r\n").encode() + multipart + f"\r\n--{limite}--\r\n".encode()
    req = urllib.request.Request(BASE + ruta, data=cuerpo, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            contenido, estado, tipo = r.read(), r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        contenido, estado, tipo = e.read(), e.code, e.headers.get("Content-Type", "")
    if estado not in esperado:
        raise AssertionError(f"{metodo} {ruta} -> {estado}: {contenido[:300]!r}")
    if crudo:
        return contenido, tipo
    return json.loads(contenido) if contenido else None


def paso(nombre, fn):
    try:
        fn()
        print(f"  OK   {nombre}")
    except Exception as e:  # noqa: BLE001
        print(f"  FALLO {nombre}: {e}")
        fallos.append(nombre)


ctx: dict = {}


def pantalla():
    html, tipo = llamar("GET", "/", crudo=True)
    assert b"SICOM" in html and "text/html" in tipo
    act, _ = llamar("GET", "/activacion/", crudo=True)
    assert b"html" in act.lower()
    det, _ = llamar("GET", f"/contrataciones/{uuid.uuid4()}/", crudo=True)
    assert b"html" in det.lower()


def licencia():
    e = llamar("GET", "/api/v1/licencia")
    assert e["operativo"] and e["obligatoria"], e
    assert len(e["id_equipo"]) == 19
    ctx["licencia"] = e


def sesion_admin():
    t = llamar("POST", "/api/v1/auth/login", datos={"username": ADMIN, "password": CLAVE_ADMIN})
    ctx["admin"] = t["access_token"]


def usuarios():
    for clave, rol in (("sol", "ROL_SOLICITANTE"), ("pre", "ROL_PRESUPUESTO"), ("rpa", "ROL_RPA")):
        nombre = f"{clave}{SUF}"
        llamar("POST", "/api/v1/admin/usuarios", ctx["admin"], {"username": nombre, "password": CLAVE, "nombre_completo": f"Usuario {clave.upper()} Prueba",
                                                               "cargo": f"Cargo {clave}", "rol": rol, "email": ""})
        ctx[clave] = llamar("POST", "/api/v1/auth/login", datos={"username": nombre, "password": CLAVE})["access_token"]


def presupuesto_y_poa():
    gestion = int(next(p["valor"] for p in llamar("GET", "/api/v1/admin/parametros", ctx["admin"]) if p["clave"] == "gestion"))
    ctx["gestion"] = gestion
    llamar("PUT", "/api/v1/admin/parametros/mae_nombre", ctx["admin"], {"valor": "Lic. Autoridad de Prueba"})
    llamar("PUT", "/api/v1/admin/parametros/mae_cargo", ctx["admin"], {"valor": "Alcalde Municipal"})
    llamar("PUT", "/api/v1/poa/objetivos", ctx["pre"], {"gestion": gestion, "programa": "777", "denominacion_programa": "PROGRAMA DE PRUEBA",
                                                       "codigo_objetivo": "OBJ77", "descripcion_objetivo": "Objetivo de prueba de la instalación"})
    p = llamar("POST", "/api/v1/partidas", ctx["pre"], {"codigo_partida": "25800", "descripcion": "Mantenimiento y reparación", "descripcion_apertura": "APERTURA DE PRUEBA",
                                                        "saldo_disponible": "90000.00", "gestion": gestion, "programa": "777", "proyecto": "0000",
                                                        "actividad": "001", "fuente": "20", "organismo": "230"})
    ctx["partida"] = p["id"]


def solicitud():
    c = llamar("POST", "/api/v1/contrataciones", ctx["sol"], {
        "objeto_contratacion": "Mantenimiento correctivo de equipos de la unidad (prueba de instalación)", "tipo_objeto": "SERVICIO_GENERAL",
        "plazo_dias_calendario": 10, "unidad_solicitante": "Unidad de Prueba", "justificacion": "Atención de la necesidad institucional programada.",
        "especificaciones_tecnicas": "Cumplir las especificaciones técnicas detalladas para el servicio solicitado.", "lugar_entrega": "Edificio municipal",
        "justificacion_poa": "El servicio asegura la continuidad operativa de la unidad y apoya el objetivo de gestión institucional."})
    ctx["cid"] = c["id"]
    llamar("POST", f"/api/v1/contrataciones/{c['id']}/items", ctx["sol"], {
        "codigo_unspsc": "", "partida_id": ctx["partida"], "descripcion_especifica": "Mantenimiento correctivo integral", "unidad_medida": "Global",
        "cantidad": "1", "precio_unitario_ref": "25000.00", "fuera_catalogo_chb": False})
    c = llamar("POST", f"/api/v1/contrataciones/{c['id']}/solicitar", ctx["sol"])
    tipos = {d["tipo_doc"] for d in c["documentos"]}
    assert {"C1_SOLICITUD", "NOTA_SOLICITUD_PAC"} <= tipos, tipos


def certificacion():
    c = llamar("POST", f"/api/v1/contrataciones/{ctx['cid']}/certificar", ctx["pre"], {"preventivo_c31_nro": "C31-2026-00001"})
    tipos = {d["tipo_doc"] for d in c["documentos"]}
    assert c["estado"] == "CERTIFICADO_PRESUPUESTO" and {"CERTIFICACION_C31", "CERTIFICACION_POA"} <= tipos, (c["estado"], tipos)
    ctx["docs"] = c["documentos"]


def pdf_con_qr_y_verificacion():
    por_tipo = {d["tipo_doc"]: d for d in ctx["docs"]}
    for tipo in ("C1_SOLICITUD", "NOTA_SOLICITUD_PAC", "CERTIFICACION_POA"):
        d = por_tipo[tipo]
        contenido, mime = llamar("GET", f"/api/v1/contrataciones/{ctx['cid']}/documentos/{d['id']}/descargar", ctx["pre"], crudo=True)
        assert mime.startswith("application/pdf") and contenido.startswith(b"%PDF"), f"{tipo}: no es un PDF ({mime})"
        assert b"/Subtype /Image" in contenido or b"/Subtype/Image" in contenido, f"{tipo}: no contiene el codigo QR (imagen)"
        ficha = llamar("GET", f"/api/v1/verificar/{d['id']}")
        assert ficha["tipo_doc"] == tipo
        r = llamar("POST", f"/api/v1/verificar/{d['id']}/archivo", multipart=contenido)
        assert r["coincide"] is True, r
        mala = llamar("POST", f"/api/v1/verificar/{d['id']}/archivo", multipart=contenido + b" alterado")
        assert mala["coincide"] is False
        pagina, _ = llamar("GET", f"/verificar/{d['id']}/", crudo=True)
        assert b"html" in pagina.lower()
    ctx["pdf_bytes"] = len(contenido)


def auditoria():
    r = llamar("GET", "/api/v1/admin/auditoria/verificar", ctx["admin"])
    assert r["ok"] is True and r["total"] > 5, r


def usuarios_limitados():
    # un solicitante no puede certificar ni importar (RBAC)
    llamar("POST", f"/api/v1/contrataciones/{ctx['cid']}/certificar", ctx["sol"], {}, esperado=(403, 409, 422))
    llamar("GET", "/api/v1/admin/usuarios", ctx["sol"], esperado=(403,))


print(f"Prueba de punta a punta: {BASE}")
for n, f in (("Pantalla web (inicio, activación, detalle)", pantalla), ("Licencia obligatoria vigente", licencia), ("Inicio de sesión del administrador", sesion_admin),
             ("Usuarios por rol creados desde el sistema", usuarios), ("Presupuesto y objetivo del POA", presupuesto_y_poa),
             ("Solicitud > Bs 20.000 (C-1 y nota PAC)", solicitud), ("Certificación (C-31 y POA)", certificacion),
             ("PDF con QR + verificación pública del archivo", pdf_con_qr_y_verificacion), ("Auditoría inalterable íntegra", auditoria),
             ("Permisos por rol", usuarios_limitados)):
    paso(n, f)
print("RESULTADO:", "FALLÓ " + ", ".join(fallos) if fallos else "TODO CORRECTO")
sys.exit(1 if fallos else 0)
