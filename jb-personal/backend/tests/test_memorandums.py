"""Memorándums de Designación, Aceptación de Renuncia y Agradecimiento: cites, efectos y control."""
import io

import docx
import pytest

G = 2027        # gestión propia de estas pruebas (no interfiere con octubre/2026 de las demás)


def _ok(r, code=200):
    assert r.status_code == code, r.text
    return r.json()


@pytest.fixture(scope="module")
def personas(client):
    out = {}
    for cod, ci, nom, ape, cargo in (("8001", "8000001", "Rita", "Prueba Designada", "Técnico"), ("8002", "8000002", "Saúl", "Prueba Renunciante", "Jefe de Unidad de Pruebas"),
                                     ("8003", "8000003", "Tina", "Prueba Cesada", "Auxiliar"), ("8004", "8000004", "Uriel", "Prueba Cerrada", "Auxiliar")):
        e = _ok(client.post("/api/empleados", json={"d": {"codigo": cod, "ci": ci, "nombres": nom, "apellidos": ape, "cargo": cargo},
                                                    "c": {"modalidad": "PERMANENTE", "haber_basico": 3000, "fecha_inicio": "2026-01-01", "partida": "11000"}}))
        out[cod] = e
    _ok(client.put("/api/memo-config", json={"prefijo": "GAMX/MAE/VYC", "encabezado": "CAPITAL DE PRUEBA\nLEY N° 1 DE PRUEBA", "lema": "¡Lema de prueba!",
                                             "pie": "Plaza principal s/n\ncontacto@example.org", "decreto_estructura": "Decreto Municipal GAMX/DMAE/DE/N°018/2025",
                                             "firmante_nombre": "Alcalde de Prueba", "firmante_cargo": "Alcalde Municipal"}))
    return out


def borrador(client, tipo, emp, fecha, efectiva, extra=None, **kw):
    datos = {"fecha_renuncia": "2027-03-10"} if tipo == "ACEPTACION_RENUNCIA" else {}
    datos.update(extra or {})
    t = _ok(client.post("/api/memorandums/texto", json={"tipo": tipo, "fecha": fecha, "fecha_efectiva": efectiva, "destinatario": emp["nombres"],
                                                          "cargo": emp["cargo"], "fecha_renuncia": datos.get("fecha_renuncia"), "datos": datos}))
    body = {"tipo": tipo, "fecha": fecha, "fecha_efectiva": efectiva, "empleado_id": emp["id"], "destinatario": f"{emp['nombres']} {emp['apellidos']}",
            "destinatario_ci": emp["ci"], "cargo": emp["cargo"], "referencia": t["referencia"], "cuerpo": t["cuerpo"], "datos": datos}
    body.update(kw)
    return _ok(client.post("/api/memorandums", json=body))


def test_textos_base_de_los_modelos(client, personas):
    e = personas["8002"]
    d = _ok(client.post("/api/memorandums/texto", json={"tipo": "DESIGNACION", "fecha": "2027-03-01", "fecha_efectiva": "2027-03-01", "cargo": e["cargo"]}))
    assert d["referencia"] == "DESIGNACIÓN DE CARGO" and "MEMORANDUM DE DESIGNACIÓN" in d["cuerpo"] and "JEFE DE UNIDAD DE PRUEBAS" in d["cuerpo"]
    assert "1 de marzo de 2027" in d["cuerpo"] and "Ley N° 2027" in d["cuerpo"]
    r = _ok(client.post("/api/memorandums/texto", json={"tipo": "ACEPTACION_RENUNCIA", "fecha": "2027-03-15", "fecha_efectiva": "2027-03-15", "fecha_renuncia": "2027-03-10", "cargo": e["cargo"]}))
    assert "Decreto Municipal GAMX/DMAE/DE/N°018/2025" in r["cuerpo"] and "tres (3) días hábiles" in r["cuerpo"] and "30 días calendario" in r["cuerpo"]
    assert "10 de marzo de 2027" in r["cuerpo"] and "RELACIÓN LABORAL" in r["cuerpo"]
    a = _ok(client.post("/api/memorandums/texto", json={"tipo": "AGRADECIMIENTO", "fecha": "2027-03-08", "fecha_efectiva": "2027-03-08", "cargo": e["cargo"]}))
    assert "SU AGRADECIMIENTO" in a["cuerpo"] and a["cuerpo"].count("\n- ") == 4 and "Alcalde de Prueba" in a["cuerpo"]
    assert "[COMPLETAR" not in a["cuerpo"]
    sin = _ok(client.post("/api/memorandums/texto", json={"tipo": "DESIGNACION", "cargo": ""}))
    assert "{" not in sin["cuerpo"]                                           # ninguna variable sin resolver queda con llaves


def test_cite_correlativo_unico_para_todos_los_tipos(client, personas):
    a = borrador(client, "DESIGNACION", personas["8001"], "2027-03-01", "2027-03-01")
    assert a["estado"] == "BORRADOR" and a["cite"] == ""                      # el borrador no consume número
    b = borrador(client, "AGRADECIMIENTO", personas["8003"], "2027-03-08", "2027-03-08", extra={"registrar_baja": False})
    e2 = _ok(client.post(f"/api/memorandums/{b['id']}/emitir"))               # emite primero el 2.º para ver que el número se asigna al emitir
    e1 = _ok(client.post(f"/api/memorandums/{a['id']}/emitir"))
    assert e2["cite"] == "GAMX/MAE/VYC/N°001/2027" and e1["cite"] == "GAMX/MAE/VYC/N°002/2027"
    assert (e1["correlativo"], e1["gestion"], e1["estado"]) == (2, 2027, "EMITIDO")
    assert client.post(f"/api/memorandums/{a['id']}/emitir").status_code == 422        # no se emite dos veces


def test_emitido_es_inalterable(client, personas):
    m = [x for x in _ok(client.get("/api/memorandums?estado=EMITIDO&gestion=2027"))][0]
    det = _ok(client.get(f"/api/memorandums/{m['id']}"))
    cuerpo = {k: det[k] for k in ("tipo", "fecha", "fecha_efectiva", "destinatario", "cargo", "cuerpo")}
    assert client.put(f"/api/memorandums/{m['id']}", json=cuerpo).status_code == 409
    assert client.delete(f"/api/memorandums/{m['id']}").status_code == 409


def test_efecto_designacion_en_contrato_y_cargo(client, personas):
    e = personas["8001"]
    det = _ok(client.get(f"/api/empleados/{e['id']}"))
    assert det["contratos"][0]["nro_documento"] == "GAMX/MAE/VYC/N°002/2027"
    memo = [x for x in _ok(client.get("/api/memorandums?tipo=DESIGNACION")) if x["empleado_id"] == e["id"]][0]
    assert "N° de documento" in memo["efecto"]


def test_campos_por_completar_bloquean_la_emision(client, personas):
    e = personas["8002"]
    body = {"tipo": "ACEPTACION_RENUNCIA", "fecha": "2027-03-15", "fecha_efectiva": "2027-03-15", "empleado_id": e["id"], "destinatario": "Saúl Prueba",
            "cargo": e["cargo"], "cuerpo": "Texto con [COMPLETAR: fecha_renuncia] pendiente de llenar por el usuario.", "datos": {}}
    m = _ok(client.post("/api/memorandums", json=body))
    r = client.post(f"/api/memorandums/{m['id']}/emitir")
    assert r.status_code == 422 and "por completar" in r.text
    assert client.delete(f"/api/memorandums/{m['id']}").status_code == 200


def test_renuncia_registra_baja_y_se_refleja_en_planillas(client, personas):
    e = personas["8002"]
    m = borrador(client, "ACEPTACION_RENUNCIA", e, "2027-03-15", "2027-03-15", extra={"registrar_baja": True})
    r = _ok(client.post(f"/api/memorandums/{m['id']}/emitir", json={"registrar_baja": True}))
    cite = r["cite"]
    assert cite.endswith("/2027") and "Baja registrada" in r["efecto"]
    c = _ok(client.get(f"/api/empleados/{e['id']}"))["contratos"][0]
    assert (c["fecha_baja"], c["causal_baja"], c["nro_documento"]) == ("2027-03-15", "RENUNCIA", cite)
    import openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(client.get("/api/reportes/2027/3/desvinculados.xlsx").content))["Desvinculados"]
    celdas = [str(x.value) for row in ws.iter_rows() for x in row if x.value]
    assert "Saúl Prueba Renunciante" in celdas and "Renuncia" in celdas and "15/03/2027" in celdas and cite in celdas     # el N° de documento es el cite del memorándum
    fila = next(r_ for r_ in ws.iter_rows(values_only=True) if r_[2] == "Saúl Prueba Renunciante")
    assert 15 in fila and 1500.0 in fila                                      # 15 días comerciales × 3000/30


def test_anular_revierte_baja_y_no_reutiliza_numero(client, personas):
    e = personas["8002"]
    m = [x for x in _ok(client.get("/api/memorandums?tipo=ACEPTACION_RENUNCIA&estado=EMITIDO")) if x["empleado_id"] == e["id"]][0]
    assert client.post(f"/api/memorandums/{m['id']}/anular", json={"motivo": "corto"}).status_code == 422
    a = _ok(client.post(f"/api/memorandums/{m['id']}/anular", json={"motivo": "Emitido con fecha incorrecta; se reemite"}))
    assert a["estado"] == "ANULADO" and a["cite"] == m["cite"]
    c = _ok(client.get(f"/api/empleados/{e['id']}"))["contratos"][0]
    assert c["fecha_baja"] is None and c["causal_baja"] == ""
    n = borrador(client, "DESIGNACION", personas["8003"], "2027-03-20", "2027-03-20")
    nuevo = _ok(client.post(f"/api/memorandums/{n['id']}/emitir"))
    assert nuevo["correlativo"] == m["correlativo"] + 1                       # el número anulado NO se reutiliza


def test_control_de_cites_y_numeros_saltados(client, personas):
    r = _ok(client.get("/api/cites/memorandum/2027"))
    assert r["emitidos"] == 3 and r["anulados"] == 1 and r["siguiente"] == r["ultimo"] + 1 and not r["saltados"]
    assert [d["estado"] for d in r["detalle"]].count("ANULADO") == 1
    ultimo = r["ultimo"]
    assert client.post("/api/cites/memorandum/siguiente", json={"gestion": 2027, "numero": ultimo, "motivo": "intento de retroceso"}).status_code == 422
    assert client.post("/api/cites/memorandum/siguiente", json={"gestion": 2027, "numero": ultimo + 10, "motivo": "corto"}).status_code == 422
    r2 = _ok(client.post("/api/cites/memorandum/siguiente", json={"gestion": 2027, "numero": ultimo + 10, "motivo": "Continuar numeración llevada en papel"}))
    assert r2["siguiente"] == ultimo + 10 and r2["saltados"] == list(range(ultimo + 1, ultimo + 10))   # 5..13 quedan a la vista como saltados
    n = borrador(client, "AGRADECIMIENTO", personas["8004"], "2027-04-01", "2027-04-01")
    assert _ok(client.post(f"/api/memorandums/{n['id']}/emitir"))["correlativo"] == ultimo + 10
    r3 = _ok(client.get("/api/cites/memorandum/2027"))
    assert r3["saltados"] == list(range(ultimo + 1, ultimo + 10))             # los números omitidos quedan a la vista para auditoría
    series = {s["serie"] for s in _ok(client.get("/api/cites"))}
    assert {"MEMORANDUM", "INSTRUCTIVO", "BOLETA"} <= series | {"MEMORANDUM", "INSTRUCTIVO", "BOLETA"}
    import openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(client.get("/api/memorandums-registro.xlsx?gestion=2027").content)).active
    est = [r_[3] for r_ in ws.iter_rows(min_row=2, values_only=True)]
    assert est.count("SALTADO") == 9 and est.count("ANULADO") == 1 and ws.cell(2, 2).value == "GAMX/MAE/VYC/N°001/2027"


def test_periodo_cerrado_bloquea_baja_sin_consumir_numero(client, personas):
    e = personas["8004"]
    _ok(client.post("/api/periodos/2027/2/procesar"))
    _ok(client.post("/api/periodos/2027/2/cerrar"))
    antes = _ok(client.get("/api/cites/memorandum/2027"))["ultimo"]
    m = borrador(client, "AGRADECIMIENTO", e, "2027-02-10", "2027-02-10", extra={"registrar_baja": True})
    r = client.post(f"/api/memorandums/{m['id']}/emitir", json={"registrar_baja": True})
    assert r.status_code == 422 and "CERRADO" in r.text
    assert _ok(client.get("/api/cites/memorandum/2027"))["ultimo"] == antes     # no se consumió el número
    assert _ok(client.get(f"/api/memorandums/{m['id']}"))["estado"] == "BORRADOR"


def test_recepcion_y_documentos(client, personas):
    m = [x for x in _ok(client.get("/api/memorandums?estado=EMITIDO&tipo=AGRADECIMIENTO")) if x["cite"]][0]
    assert client.post(f"/api/memorandums/{m['id']}/recepcion", json={"fecha": "2000-01-01"}).status_code == 422
    r = _ok(client.post(f"/api/memorandums/{m['id']}/recepcion", json={"fecha": "2027-06-30", "recibido_por": "Tina Prueba"}))
    assert r["recibido_fecha"] == "2027-06-30"
    pdf = client.get(f"/api/memorandums/{m['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and len(pdf.content) > 3000
    w = docx.Document(io.BytesIO(client.get(f"/api/memorandums/{m['id']}/docx").content))
    texto = "\n".join(p.text for p in w.paragraphs) + "\n".join(c.text for t in w.tables for row in t.rows for c in row.cells)
    assert m["cite"] in texto and "M E M O R Á N D U M" in texto and "SU AGRADECIMIENTO" in texto and "Recibido: 30/06/2027" in texto
    b = borrador(client, "DESIGNACION", personas["8001"], "2027-05-01", "2027-05-01")
    assert client.get(f"/api/memorandums/{b['id']}/pdf").content[:4] == b"%PDF"          # el borrador también se previsualiza (marca de agua)
    assert "BORRADOR" in "\n".join(p.text for p in docx.Document(io.BytesIO(client.get(f"/api/memorandums/{b['id']}/docx").content)).paragraphs)


def test_logo_y_membrete(client, personas):
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (40, 30), (200, 80, 20)).save(buf, "PNG")
    assert client.post("/api/memo-config/logo", files={"archivo": ("l.png", buf.getvalue())}).status_code == 200
    assert client.post("/api/memo-config/logo", files={"archivo": ("l.exe", b"MZ....")}).status_code == 422
    assert client.get("/api/memo-config/logo").headers["content-type"] == "image/png"
    assert client.get("/api/memo-config").json()["tiene_logo"] is True
    m = [x for x in _ok(client.get("/api/memorandums?estado=EMITIDO"))][0]
    assert client.get(f"/api/memorandums/{m['id']}/pdf").content[:4] == b"%PDF"


def test_plantilla_editable_y_restaurable(client, personas):
    p = [x for x in _ok(client.get("/api/memo-plantillas")) if x["tipo"] == "AGRADECIMIENTO"][0]
    _ok(client.put("/api/memo-plantillas/AGRADECIMIENTO", json={"referencia": "AGRADECIMIENTO PERSONALIZADO", "cuerpo": "Texto propio para {destinatario} en el cargo {cargo}, con efecto desde {fecha_efectiva}."}))
    t = _ok(client.post("/api/memorandums/texto", json={"tipo": "AGRADECIMIENTO", "destinatario": "Ana", "cargo": "Jefa", "fecha_efectiva": "2027-01-05"}))
    assert t["referencia"] == "AGRADECIMIENTO PERSONALIZADO" and t["cuerpo"].startswith("Texto propio para Ana en el cargo Jefa, con efecto desde 5 de enero de 2027")
    _ok(client.post("/api/memo-plantillas/AGRADECIMIENTO/restaurar"))
    assert _ok(client.get("/api/memo-plantillas"))[0]["cuerpo"] and "SU AGRADECIMIENTO" in [x for x in _ok(client.get("/api/memo-plantillas")) if x["tipo"] == "AGRADECIMIENTO"][0]["cuerpo"]


def test_roles(client, personas):
    _ok(client.post("/api/usuarios", json={"username": "lector3", "password": "Lector#2026", "rol": "CONSULTA"}))
    tok = _ok(client.post("/api/auth/login", json={"username": "lector3", "password": "Lector#2026"}))["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/memorandums", headers=h).status_code == 200
    assert client.post("/api/memorandums/1/emitir", headers=h).status_code == 403
    assert client.post("/api/cites/memorandum/siguiente", json={"gestion": 2027, "numero": 99, "motivo": "intento no autorizado"}, headers=h).status_code == 403


def test_plantilla_no_evalua_expresiones(client, personas):
    """Una plantilla maliciosa no puede leer atributos ni objetos internos: solo se sustituyen {identificadores}."""
    _ok(client.put("/api/memo-plantillas/DESIGNACION", json={"referencia": "DESIGNACIÓN DE CARGO", "cuerpo": "A {entidad.__class__} B {entidad.__init__.__globals__} C {cargo[0]} D {desconocida} E {cargo}."}))
    t = _ok(client.post("/api/memorandums/texto", json={"tipo": "DESIGNACION", "cargo": "Jefe", "fecha_efectiva": "2027-01-05"}))
    assert "__class__" in t["cuerpo"] and "<class" not in t["cuerpo"] and "globals" in t["cuerpo"] and "{cargo[0]}" in t["cuerpo"]     # se dejan tal cual
    assert "[COMPLETAR: desconocida]" in t["cuerpo"] and t["cuerpo"].endswith("E Jefe.")
    _ok(client.post("/api/memo-plantillas/DESIGNACION/restaurar"))
