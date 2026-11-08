"""Caso de uso real de punta a punta con el dataset de prueba (octubre 2026).

Los valores ESPERADOS se calcularon a mano (ver docs/GUIA_PRUEBAS.md), no se copiaron de la salida del sistema.
"""
import csv
import io
from decimal import Decimal as D

import openpyxl
import pytest

from conftest import DATOS


def _ok(r, code=200):
    assert r.status_code == code, r.text
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else r


def _post_file(c, url, path, **data):
    with open(path, "rb") as f:
        return c.post(url, files={"archivo": (path.name, f)}, data=data)


@pytest.fixture(scope="module")
def cargado(client):
    c = client
    ent = _ok(c.get("/api/entidad"))
    ent.update(nombre="Gobierno Autónomo Municipal de Villa Ejemplo", sigla="VE", ciudad="Villa Ejemplo", codigo_sigep="01-913-00099",
               mae_nombre="Ana Ejemplo Lima", rrhh_nombre="Pedro Prueba Rojas", aprobador_nombre="Rosa Modelo Vega",
               reglamento_rip="Decreto Edil N° 012/2024")
    _ok(c.put("/api/entidad", json=ent))
    r = _ok(_post_file(c, "/api/personal/importar", DATOS / "personal.csv"))
    assert r["creados"] == 5 and not r["errores"], r
    ids = {e["codigo"]: e["id"] for e in _ok(c.get("/api/empleados"))}
    r = _ok(_post_file(c, "/api/biometrico/importar", DATOS / "biometrico_octubre_2026.csv"))
    assert (r["leidas"], r["nuevas"], r["duplicadas"], r["rechazadas"]) == (408, 408, 0, 0)
    with open(DATOS / "permisos_octubre_2026.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            body = {"empleado_id": ids[row["codigo_empleado"]], "tipo_codigo": row["tipo"], "fecha_desde": row["desde"],
                    "fecha_hasta": row["hasta"], "motivo": row["motivo"], "doc_respaldo": row["doc_respaldo"],
                    "autorizado_por": row["autorizado_por"], "aprobar": row["estado"] == "APROBADO"}
            if row["hora_desde"]:
                body["hora_desde"], body["hora_hasta"] = row["hora_desde"], row["hora_hasta"]
            _ok(c.post("/api/permisos", json=body))
    _ok(c.post("/api/periodos/2026/10/procesar"))
    return ids


def liq(c):
    return {x["ci"]: x for x in _ok(c.get("/api/liquidacion/2026/10"))}


def test_liquidacion_valores_esperados(client, cargado):
    L = liq(client)
    # (laborables, asistidos, faltas, min_retraso, nro_retrasos, justificados, dias_desc, ganado, afp, desc_asist, liquido)
    esperado = {
        "1000001": (22, 22, 0, 30, 2, 0, "0", "6000.00", "762.60", "0.00", "5237.40"),
        "1000002": (22, 21, 1, 70, 2, 0, "2.5", "4500.00", "571.95", "375.00", "3553.05"),
        "1000003": (22, "19.5", "0.5", 0, 0, 2, "1", "3800.00", "482.98", "126.67", "3190.35"),
        "1000004": (22, 21, 0, 22, 1, 1, "1", "3500.00", "444.85", "116.67", "2938.48"),
        "1000005": (22, 19, 1, 50, 1, 2, "2", "7000.00", "0.00", "466.66", "6533.34"),
    }
    for ci, (lab, asi, fal, mins, nro, jus, dd, gan, afp, da, liqd) in esperado.items():
        x = L[ci]
        got = (x["dias_laborables"], x["dias_asistidos"], x["faltas"], x["min_retraso"], x["nro_retrasos"],
               x["dias_justificados"], x["dias_descuento"])
        assert got == (float(lab), float(asi), float(fal), mins, nro, float(jus), float(dd)), (ci, got)
        assert D(str(x["total_ganado"])) == D(gan) and D(str(x["aporte_laboral"])) == D(afp), ci
        assert D(str(x["desc_asistencia"])) == D(da) and D(str(x["liquido_pagable"])) == D(liqd), (ci, x)


def test_sanciones_y_observaciones(client, cargado):
    L = liq(client)
    assert L["1000001"]["sancion"] == ""                       # 30 min: sin sanción
    assert "0.5" in L["1000002"]["sancion"]                     # 61-90 min: medio día
    assert L["1000005"]["sancion"] == "Amonestación escrita"    # 50 min
    assert "excede el máximo contractual" in L["1000005"]["observacion"]
    assert L["1000005"]["aporte_laboral"] == 0                  # consultor: sin aporte laboral


def test_estados_diarios(client, cargado):
    ids = cargado
    est = {(a["fecha"]): a for a in _ok(client.get(f"/api/asistencia/2026/10?empleado_id={ids['1002']}"))}
    assert est["2026-10-07"]["estado"] == "RETRASO_GRAVE" and est["2026-10-07"]["min_retraso"] == 45
    assert est["2026-10-15"]["estado"] == "FALTA_INJUSTIFICADA" and est["2026-10-15"]["falta"] == 1
    assert est["2026-10-03"]["estado"] == "NO_LABORABLE"
    e3 = {a["fecha"]: a for a in _ok(client.get(f"/api/asistencia/2026/10?empleado_id={ids['2001']}"))}
    assert e3["2026-10-12"]["estado"] == "FALTA_JUSTIFICADA" and e3["2026-10-21"]["estado"] == "NORMAL"
    assert e3["2026-10-28"]["falta"] == 0.5
    e1 = {a["fecha"]: a for a in _ok(client.get(f"/api/asistencia/2026/10?empleado_id={ids['1001']}"))}
    assert e1["2026-10-14"]["estado"] == "OMISION_MARCACION"
    e5 = {a["fecha"]: a for a in _ok(client.get(f"/api/asistencia/2026/10?empleado_id={ids['3001']}"))}
    assert e5["2026-10-27"]["estado"] == "FALTA_INJUSTIFICADA"      # permiso PENDIENTE no justifica


def test_consultor_permiso_requiere_fiscal(client, cargado):
    body = {"empleado_id": cargado["3001"], "tipo_codigo": "PARTICULAR_CGH", "fecha_desde": "2026-10-27",
            "fecha_hasta": "2026-10-27", "aprobar": True}
    r = client.post("/api/permisos", json=body)
    assert r.status_code == 422 and "fiscal" in r.text


def test_aprobar_permiso_pendiente_actualiza_motor(client, cargado):
    pend = [p for p in _ok(client.get("/api/permisos?estado=PENDIENTE"))][0]
    _ok(client.post(f"/api/permisos/{pend['id']}/aprobar", json={"autorizado_por": "Ing. Fiscal de Obra"}))
    x = liq(client)["1000005"]
    # ahora 3 días justificados: 2 de exceso, sin falta => descuento 2 días de 7000/30
    assert x["faltas"] == 0 and x["dias_justificados"] == 3 and x["desc_asistencia"] == 466.67
    # volver al estado original para no afectar a las demás pruebas
    _ok(client.post(f"/api/permisos/{pend['id']}/anular"))
    assert liq(client)["1000005"]["liquido_pagable"] == 6533.34


def test_reimportar_mismo_archivo_rechazado(client, cargado):
    r = _post_file(client, "/api/biometrico/importar", DATOS / "biometrico_octubre_2026.csv")
    assert r.status_code == 422 and "ya fue importado" in r.text


def test_reimportar_otro_formato_no_duplica(client, cargado):
    r = _ok(_post_file(client, "/api/biometrico/importar", DATOS / "biometrico_octubre_2026.xlsx"))
    # mismas marcas (mismo ID, fecha-hora y dispositivo) en otro formato de archivo => todas duplicadas, ninguna nueva
    assert r["nuevas"] == 0 and r["duplicadas"] == 408


# ------------------------------------------------------------------ reportes
def _wb(resp):
    return openpyxl.load_workbook(io.BytesIO(resp.content))


def test_reporte_planilla_sueldos(client, cargado):
    r = _ok(client.get("/api/reportes/2026/10/planilla.xlsx"))
    ws = _wb(r)["Planilla"]
    textos = [str(c.value) for row in ws.iter_rows() for c in row if c.value]
    assert any("PERSONAL PERMANENTE" in t for t in textos) and any("CONSULTORES" in t for t in textos)
    assert any(t.startswith("=SUM(") for t in textos)
    rs = _wb(r)["Resumen"]
    assert rs["B5"].value == 2 and rs["B6"].value == 2 and rs["B7"].value == 1
    assert rs["C5"].value == 10500 and abs(rs["H7"].value - 6533.34) < 1e-6


def test_reporte_nuevos_y_desvinculados(client, cargado):
    nuevos = _wb(_ok(client.get("/api/reportes/2026/10/nuevos.xlsx")))["Nuevos"]
    nombres = [str(c.value) for row in nuevos.iter_rows() for c in row if c.value]
    assert "Carla Andrea Flores Apaza" in nombres and "Juan Carlos Mamani Quispe" not in nombres
    baj = _wb(_ok(client.get("/api/reportes/2026/10/desvinculados.xlsx")))["Desvinculados"]
    nombres = [str(c.value) for row in baj.iter_rows() for c in row if c.value]
    assert "Miguel Ángel Salazar Copa" in nombres and "Conclusión de contrato" in nombres and "30/10/2026" in nombres


def test_reporte_asistencia_detalle(client, cargado):
    wb = _wb(_ok(client.get("/api/reportes/2026/10/asistencia.xlsx")))
    assert set(wb.sheetnames) == {"Resumen institucional", "Detalle diario", "Faltas y retrasos", "Leyenda"}
    # 4 servidores con 31 días de contrato en el mes + el consultor hasta el 30/10 (30 días) = 154 filas de detalle
    assert wb["Detalle diario"].max_row == 4 + 4 * 31 + 30
    imput = [r for r in wb["Faltas y retrasos"].iter_rows(min_row=5, values_only=True)]
    from collections import Counter
    assert Counter(r[3] for r in imput) == {"Retraso leve": 4, "Retraso grave": 2, "Falta injustificada": 3, "Falta justificada": 5, "Omisión de marcación": 2}


def test_reporte_plano_auditoria(client, cargado):
    r = _ok(client.get("/api/reportes/2026/10/auditoria.txt"))
    txt = r.content.decode("utf-8")
    assert not r.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(txt), delimiter="\t"))
    assert rows[0] == ["PERIODO", "CI", "CODIGO_EMPLEADO", "TIPO_CONTRATO", "TOTAL_DIAS_LABORABLES", "DIAS_ASISTIDOS", "FALTAS",
                       "MINUTOS_RETRASO", "DIAS_PERMISO_JUSTIFICADO", "IMPORTE_DESCUENTOS_APLICADOS"]
    body = {r[1]: r for r in rows[1:]}
    assert body["1000002"] == ["2026-10", "1000002", "1002", "PERMANENTE", "22", "21.00", "1.00", "70", "0.00", "375.00"]
    assert body["1000005"] == ["2026-10", "1000005", "3001", "CONSULTOR_LINEA", "22", "19.00", "1.00", "50", "2.00", "466.66"]
    assert len(rows) == 6
    coma = _ok(client.get("/api/reportes/2026/10/auditoria.txt?delimitador=coma&bom=true"))
    assert coma.content.startswith(b"\xef\xbb\xbf") and b"," in coma.content


def test_informe_docx(client, cargado):
    import docx
    r = _ok(client.get("/api/reportes/2026/10/informe.docx"))
    d = docx.Document(io.BytesIO(r.content))
    texto = "\n".join(p.text for p in d.paragraphs) + "\n".join(c.text for t in d.tables for row in t.rows for c in row.cells)
    assert "[" not in texto.replace("[PENDIENTE]", ""), [m for m in texto.split("\n") if "[" in m][:5]
    assert "octubre de 2026" in texto and "22 días hábiles" in texto and "Vargas Rojas María Elena" in texto
    assert "70 min" in texto and "BORRADOR" in texto
    t_res = d.tables[1]
    assert t_res.rows[1].cells[1].text.isdigit()
    # emitir asigna correlativo
    r2 = _ok(client.get("/api/reportes/2026/10/informe.docx?emitir=true"))
    d2 = docx.Document(io.BytesIO(r2.content))
    assert "INF-ASIST/N° 001/2026" in "\n".join(p.text for p in d2.paragraphs)


def test_vacaciones_en_informe_y_se_revierte(client, cargado):
    """15/10 era falta injustificada de 1002 (sin marcas): al aprobar una vacación ese día pasa a justificada."""
    import docx
    antes = liq(client)["1000002"]
    assert antes["faltas"] == 1
    p = _ok(client.post("/api/permisos", json={"empleado_id": cargado["1002"], "tipo_codigo": "VACACION", "fecha_desde": "2026-10-15",
                                               "fecha_hasta": "2026-10-15", "gestion_vacacion": "2025-2026", "saldo_vacacion": "17 días",
                                               "autorizado_por": "Jefe inmediato", "aprobar": True}))
    x = liq(client)["1000002"]
    assert (x["faltas"], x["dias_justificados"], x["desc_asistencia"], x["dias_asistidos"]) == (0, 1, 75.0, 21)   # solo queda el descuento por atrasos
    d = docx.Document(io.BytesIO(_ok(client.get("/api/reportes/2026/10/informe.docx")).content))
    fila = [c.text for c in d.tables[3].rows[1].cells]
    assert fila[1] == "Vargas Rojas María Elena" and fila[3] == "2025-2026" and fila[4] == "15/10/2026 al 15/10/2026" and fila[5] == "1 día(s)" and fila[6] == "17 días"
    _ok(client.post(f"/api/permisos/{p['id']}/anular"))
    assert liq(client)["1000002"] == antes


def test_informe_sin_procesar_da_error_claro(client, cargado):
    r = client.get("/api/reportes/2026/9/planilla.xlsx")
    assert r.status_code == 422 and "no fue procesado" in r.text


# ------------------------------------------------------------------ cierre, auditoría, permisos
def test_cierre_de_periodo_bloquea(client, cargado):
    _ok(client.post("/api/periodos/2026/10/cerrar"))
    assert client.post("/api/periodos/2026/10/procesar").status_code == 422
    r = client.post("/api/permisos", json={"empleado_id": cargado["1001"], "tipo_codigo": "PARTICULAR_CGH",
                                           "fecha_desde": "2026-10-30", "fecha_hasta": "2026-10-30"})
    assert r.status_code == 422 and "CERRADO" in r.text
    assert client.post("/api/periodos/2026/10/reabrir", json={"motivo": "corto"}).status_code == 422
    _ok(client.post("/api/periodos/2026/10/reabrir", json={"motivo": "Corrección autorizada por la MAE"}))


def test_bitacora_inalterable_y_cadena(client, cargado):
    assert _ok(client.get("/api/auditoria/verificar"))["ok"] is True
    from app.db import engine
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    with pytest.raises(DBAPIError):
        with engine.begin() as con:
            con.execute(text("UPDATE audit_log SET usuario='x' WHERE id=1"))
    with pytest.raises(DBAPIError):
        with engine.begin() as con:
            con.execute(text("DELETE FROM audit_log"))
    with pytest.raises(DBAPIError):
        with engine.begin() as con:
            con.execute(text("UPDATE marca SET identificador='9' WHERE id=1"))


def test_boleta_y_instructivo(client, cargado):
    p = _ok(client.get("/api/permisos?empleado_id=%d" % cargado["2001"]))[0]
    assert p["nro_boleta"].startswith("GAM-RRHH-BOL-") and p["nro_boleta"].endswith("/2026")
    pdf = _ok(client.get(f"/api/permisos/{p['id']}/boleta.pdf"))
    assert pdf.content[:4] == b"%PDF"
    i = _ok(client.post("/api/instructivos", json={"titulo": "Uso obligatorio del biométrico",
                                                    "contenido": "Se instruye marcar entrada y salida.\n\nBajo responsabilidad.",
                                                    "modalidades": ["PERMANENTE"], "cargos": ["inspector"]}))
    assert i["cite"] == "GAM-RRHH-INST-001/2026" and i["n_destinatarios"] == 3
    j = _ok(client.post("/api/instructivos", json={"titulo": "Todos", "contenido": "Texto del comunicado general.", "todos": True}))
    assert j["cite"] == "GAM-RRHH-INST-002/2026" and j["n_destinatarios"] == 5
    assert client.post("/api/instructivos", json={"titulo": "Nadie", "contenido": "Texto del comunicado.", "cargos": ["zzz"]}).status_code == 422
    _ok(client.post(f"/api/instructivos/{i['id']}/emitir"))
    d = _ok(client.get(f"/api/instructivos/{i['id']}"))["destinatarios"][0]
    _ok(client.put(f"/api/instructivos/{i['id']}/destinatarios/{d['id']}", json={"notificacion": "NOTIFICADO"}))
    assert _ok(client.get(f"/api/instructivos/{i['id']}/pdf")).content[:4] == b"%PDF"


def test_backup_cifrado_y_restauracion(client, cargado):
    assert client.post("/api/backup", json={"password": "corta"}).status_code == 422
    b = _ok(client.post("/api/backup", json={"password": "Respaldo-Seguro-1"}))
    f = b["ruta"]
    blob = open(f, "rb").read()
    assert b"CREATE TABLE" not in blob and b"Mamani" not in blob          # cifrado
    ok = _ok(client.post("/api/backup/verificar", files={"archivo": ("b.enc", blob)}, data={"sha256": b["sha256"], "password": "Respaldo-Seguro-1"}))
    assert ok["integridad"] == "OK"
    assert client.post("/api/backup/verificar", files={"archivo": ("b.enc", blob)}, data={"sha256": "0" * 64}).status_code == 422
    assert client.post("/api/backup/verificar", files={"archivo": ("b.enc", blob)}, data={"sha256": b["sha256"], "password": "equivocada"}).status_code == 422
    alterado = blob[:-1] + bytes([blob[-1] ^ 1])
    assert client.post("/api/backup/verificar", files={"archivo": ("b.enc", alterado)}, data={"sha256": b["sha256"]}).status_code == 422
    # restauración: modificar datos, restaurar y comprobar que vuelven
    n_antes = len(_ok(client.get("/api/empleados")))
    r = _ok(client.post("/api/backup/restaurar", files={"archivo": ("b.enc", blob)}, data={"sha256": b["sha256"], "password": "Respaldo-Seguro-1"}))
    assert r["restaurado"] is True
    assert len(_ok(client.get("/api/empleados"))) == n_antes


def test_roles_consulta_no_escribe(client, cargado):
    _ok(client.post("/api/usuarios", json={"username": "lector", "password": "Lector#2026", "rol": "CONSULTA"}))
    tok = _ok(client.post("/api/auth/login", json={"username": "lector", "password": "Lector#2026"}))["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/empleados", headers=h).status_code == 200
    assert client.post("/api/periodos/2026/10/procesar", headers=h).status_code == 403
    assert client.post("/api/backup", json={"password": "Respaldo-Seguro-1"}, headers=h).status_code == 403
    assert client.get("/api/empleados", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_sin_token_401(client):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as anon:
        assert anon.get("/api/empleados").status_code == 401
        assert anon.post("/api/auth/setup", json={"username": "otro", "password": "Otro#2026!!"}).status_code == 409


def test_inyeccion_de_formulas_en_excel(client, cargado):
    """Un nombre que empieza por '=' se guarda como texto en los reportes (no como fórmula)."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["codigo", "ci", "nombres", "apellidos", "modalidad", "haber_basico", "fecha_ingreso"])
    ws.append(["9001", "9000001", '=HYPERLINK("http://malo.example","clic")', "Prueba Inyeccion", "Permanente", 3000, "01/10/2026"])
    ws.append(["9002", "=cmd|' /C calc'!A0", "Otro", "Malo", "Permanente", 3000, "01/10/2026"])
    for celda in ("C2", "B3"):          # texto que el usuario escribió (no fórmula real)
        ws[celda].data_type = "s"
    buf = io.BytesIO(); wb.save(buf)
    r = _ok(client.post("/api/personal/importar", files={"archivo": ("inj.xlsx", buf.getvalue())}))
    assert r["creados"] == 1 and len(r["errores"]) == 1 and "C.I." in r["errores"][0]
    _ok(client.post("/api/periodos/2026/10/procesar"))
    ws2 = _wb(_ok(client.get("/api/reportes/2026/10/planilla.xlsx")))["Planilla"]
    celdas = [c for row in ws2.iter_rows() for c in row if isinstance(c.value, str) and "HYPERLINK" in c.value]
    assert celdas and all(c.data_type == "s" for c in celdas)
    ws3 = _wb(_ok(client.get("/api/reportes/2026/10/asistencia.xlsx")))["Resumen institucional"]
    assert all(c.data_type == "s" for row in ws3.iter_rows() for c in row if isinstance(c.value, str) and "HYPERLINK" in c.value)
