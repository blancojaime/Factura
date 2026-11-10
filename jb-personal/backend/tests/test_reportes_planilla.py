"""Regresión: las planillas deben mostrar a TODOS los empleados aunque se hayan cargado después de 'Procesar'."""
import io

import openpyxl
import pytest


def _wb(r):
    assert r.status_code == 200, r.text
    return openpyxl.load_workbook(io.BytesIO(r.content))


def _nombres(ws):
    return [str(c.value) for row in ws.iter_rows() for c in row if c.value]


@pytest.fixture(scope="module")
def agosto(client):
    base = {"modalidad": "Permanente", "haber_basico": 3000, "fecha_ingreso": "01/03/2020"}
    import csv as _csv
    buf = io.StringIO()
    w = _csv.writer(buf, delimiter=";")
    w.writerow(["codigo", "ci", "nombres", "apellidos", "modalidad", "haber_basico", "fecha_ingreso", "estado"])
    w.writerow(["7001", "7000001", "Ana", "Antigua Prueba", "Permanente", 3000, "01/03/2020", "Activo"])
    r = client.post("/api/personal/importar", files={"archivo": ("p.csv", buf.getvalue().encode())})
    assert r.status_code == 200 and r.json()["creados"] == 1
    # se procesa agosto ANTES de cargar a los siguientes (escenario del error reportado)
    assert client.post("/api/periodos/2026/8/procesar").status_code == 200
    emp = client.post("/api/empleados", json={
        "d": {"codigo": "7002", "ci": "7000002", "nombres": "Beto", "apellidos": "Tardío Prueba", "cargo": "Auxiliar"},
        "c": {"modalidad": "EVENTUAL", "haber_basico": 3000, "fecha_inicio": "2026-08-10", "partida": "12100"}})
    assert emp.status_code == 200, emp.text
    cid = emp.json()["contratos"][0]["id"]
    assert client.post(f"/api/contratos/{cid}/baja", json={"fecha": "2026-08-20", "causal": "RENUNCIA"}).status_code == 200
    return True


def test_planilla_sueldos_incluye_a_los_cargados_despues_de_procesar(client, agosto):
    ws = _wb(client.get("/api/reportes/2026/8/planilla.xlsx"))["Planilla"]
    n = _nombres(ws)
    assert "Ana Antigua Prueba" in n and "Beto Tardío Prueba" in n
    fila = next(r for r in ws.iter_rows(values_only=True) if r[2] == "Beto Tardío Prueba")
    assert 11 in fila and 1100.0 in fila                       # 11 días comerciales (10..20/08) × 3000/30


def test_planilla_nuevos_y_desvinculados(client, agosto):
    nuevos = _nombres(_wb(client.get("/api/reportes/2026/8/nuevos.xlsx"))["Nuevos"])
    assert "Beto Tardío Prueba" in nuevos and "Ana Antigua Prueba" not in nuevos and "10/08/2026" in nuevos
    baj = _nombres(_wb(client.get("/api/reportes/2026/8/desvinculados.xlsx"))["Desvinculados"])
    assert "Beto Tardío Prueba" in baj and "Renuncia" in baj and "20/08/2026" in baj


def test_cabeceras_combinadas_sin_solapes(client, agosto):
    for url, hoja in (("planilla", "Planilla"), ("nuevos", "Nuevos"), ("desvinculados", "Desvinculados")):
        ws = _wb(client.get(f"/api/reportes/2026/8/{url}.xlsx"))[hoja]
        rangos = [(r.min_row, r.max_row, r.min_col, r.max_col) for r in ws.merged_cells.ranges]
        for i, a in enumerate(rangos):
            for b in rangos[i + 1:]:
                solapa = not (a[1] < b[0] or b[1] < a[0] or a[3] < b[2] or b[3] < a[2])
                assert not solapa, (url, a, b)


def test_auditoria_xlsx_plano(client, agosto):
    ws = _wb(client.get("/api/reportes/2026/8/auditoria.xlsx"))["Consolidado"]
    filas = list(ws.iter_rows(values_only=True))
    assert filas[0] == ("PERIODO", "CI", "CODIGO_EMPLEADO", "TIPO_CONTRATO", "TOTAL_DIAS_LABORABLES", "DIAS_ASISTIDOS", "FALTAS",
                        "MINUTOS_RETRASO", "DIAS_PERMISO_JUSTIFICADO", "IMPORTE_DESCUENTOS_APLICADOS")
    assert not ws.merged_cells.ranges and ws.max_row == len(filas) and len(filas) >= 3
    assert all(isinstance(f[4], (int, float)) and isinstance(f[9], (int, float)) for f in filas[1:])
    assert {f[1] for f in filas[1:]} >= {"7000001", "7000002"}


def test_periodo_cerrado_usa_lo_congelado(client, agosto):
    assert client.post("/api/periodos/2026/8/cerrar").status_code == 200
    antes = _nombres(_wb(client.get("/api/reportes/2026/8/planilla.xlsx"))["Planilla"])
    assert "Beto Tardío Prueba" in antes
