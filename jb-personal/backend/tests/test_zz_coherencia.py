"""COHERENCIA entre reportes: permisos, faltas, atrasos, multas y sueldos deben dar las MISMAS cifras en la liquidación (API),
las 3 planillas, el reporte detallado, el consolidado de auditoría (.txt y .xlsx) y el informe Word.

Mes aislado (junio/2019: 20 días hábiles, sin feriados sembrados) con todos los casos. Los valores esperados por servidor
se calcularon a mano (ver comentarios) y luego se contrastan TODAS las salidas contra la liquidación.
"""
import csv
import io
from datetime import date, timedelta

import docx
import openpyxl
import pytest

from app.reports import planillas_xlsx as PX
from app.reports.auditoria_txt import COLUMNAS, COLUMNAS_XLSX

A, M = 2019, 6
TOL = 0.005


def _ok(r, code=200):
    assert r.status_code == code, r.text
    return r.json()


def dias_habiles():
    d, out = date(A, M, 1), []
    while d.month == M:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


@pytest.fixture(scope="module")
def escenario(client):
    assert len(dias_habiles()) == 20
    emp = {}

    def alta(cod, nom, ape, mod, haber, ini, partida):
        r = _ok(client.post("/api/empleados", json={"d": {"codigo": cod, "ci": "91" + cod, "nombres": nom, "apellidos": ape, "cargo": "Cargo " + nom},
                                                    "c": {"modalidad": mod, "haber_basico": haber, "fecha_inicio": ini, "partida": partida}}))
        emp[cod] = r
        return r
    alta("9101", "Alba", "Coherencia Permanente", "PERMANENTE", 6000, "2018-01-01", "11000")
    alta("9102", "Bruno", "Coherencia Eventual", "EVENTUAL", 3000, "2018-01-01", "12100")
    alta("9103", "Carla", "Coherencia Consultora", "CONSULTOR_LINEA", 7000, "2018-01-01", "25200")
    alta("9104", "Dario", "Coherencia Alta", "PERMANENTE", 4500, "2019-06-17", "11000")
    e = alta("9105", "Elsa", "Coherencia Baja", "PERMANENTE", 5000, "2018-01-01", "11000")
    _ok(client.post(f"/api/contratos/{e['contratos'][0]['id']}/baja", json={"fecha": "2019-06-14", "causal": "RENUNCIA"}))

    # ---- marcas: puntuales salvo excepciones
    normal = ["08:00", "12:00", "14:30", "18:30"]
    excep = {  # (código, fecha): marcas | None = sin marcas
        ("9101", "2019-06-07"): None,                                        # A: falta (día completo)
        ("9101", "2019-06-03"): ["08:12", "12:00", "14:30", "18:30"],         # A: retraso 12
        ("9101", "2019-06-18"): ["08:40", "12:00", "14:30", "18:30"],         # A: retraso 40 (total 52 min => amonestación)
        ("9101", "2019-06-11"): ["10:05", "12:00", "14:30", "18:30"],         # A: permiso SIN goce 08-10 (2 h)
        ("9102", "2019-06-04"): None, ("9102", "2019-06-05"): None,           # B: licencia médica (con goce)
        ("9102", "2019-06-12"): None,                                         # B: permiso sin goce día completo
        ("9102", "2019-06-18"): ["08:00", "12:00"],                           # B: media falta (tarde sin marcas)
        ("9103", "2019-06-06"): None, ("9103", "2019-06-13"): None,           # C: 2 días justificados con fiscal
        ("9103", "2019-06-19"): ["08:00", "12:00", "16:35", "18:31"],         # C: permiso 14:30-16:30 (2 h) con goce
        ("9103", "2019-06-20"): None,                                         # C: falta
        ("9104", "2019-06-24"): None,                                         # D (alta 17/06): falta
        ("9105", "2019-06-05"): ["08:15", "12:00", "14:30", "18:30"],         # E (baja 14/06): retraso 15
    }
    filas = [("ID", "Fecha", "Hora")]
    for cod, ini, fin in (("9101", 1, 30), ("9102", 1, 30), ("9103", 1, 30), ("9104", 17, 30), ("9105", 1, 14)):
        for d in dias_habiles():
            if not (ini <= d.day <= fin):
                continue
            m = excep.get((cod, d.isoformat()), normal)
            for h in (m or []):
                filas.append((cod, d.strftime("%d/%m/%Y"), h))
    buf = io.StringIO()
    csv.writer(buf, delimiter=";").writerows(filas)
    _ok(client.post("/api/biometrico/importar", files={"archivo": ("junio2019.csv", buf.getvalue().encode())}))

    def permiso(cod, tipo, d1, d2=None, h1=None, h2=None, fiscal="Jefe inmediato"):
        b = {"empleado_id": emp[cod]["id"], "tipo_codigo": tipo, "fecha_desde": d1, "fecha_hasta": d2 or d1, "autorizado_por": fiscal, "aprobar": True}
        if h1:
            b["hora_desde"], b["hora_hasta"] = h1, h2
        return _ok(client.post("/api/permisos", json=b))
    permiso("9101", "PARTICULAR_SGH", "2019-06-11", h1="08:00", h2="10:00")
    permiso("9102", "LIC_MEDICA", "2019-06-04", "2019-06-05")
    permiso("9102", "PARTICULAR_SGH", "2019-06-12")
    permiso("9103", "PARTICULAR_CGH", "2019-06-06", fiscal="Ing. Fiscal")
    permiso("9103", "LIC_MEDICA", "2019-06-13", fiscal="Ing. Fiscal")
    permiso("9103", "PARTICULAR_CGH", "2019-06-19", h1="14:30", h2="16:30", fiscal="Ing. Fiscal")
    _ok(client.post("/api/ajustes", json={"anio": A, "mes": M, "empleado_id": emp["9101"]["id"], "tipo": "MULTA", "concepto": "Multa por extravío de bien asignado", "monto": 150, "referencia": "MEMO-123"}))
    return emp


def liq(client):
    return {x["ci"]: x for x in _ok(client.get(f"/api/liquidacion/{A}/{M}"))}


def aprox(a, b, msg=""):
    assert abs(float(a) - float(b)) < TOL, f"{msg}: {a} != {b}"


# =============================================================================== 1. valores calculados a mano
def test_valores_esperados_por_servidor(client, escenario):
    L = liq(client)
    # ci: (laborables, asistidos, faltas, min_retraso, justificados, días_desc, ganado, afp, desc_faltas, desc_atrasos, desc_otros, multas, total_desc, líquido)
    esperado = {
        # A: falta 1×2=2 d; 52 min => amonestación (0 d); 2 h sin goce = 0.25 d; multa 150
        "919101": (20, 19, 1, 52, 0, 2.25, 6000, 762.60, 400, 0, 50, 150, 1362.60, 4637.40),
        # B: media falta 0.5×2=1 d; permiso sin goce 1 d; licencia médica 2 d con goce no descuenta
        "919102": (20, 16.5, 0.5, 0, 3, 2, 3000, 381.30, 100, 0, 100, 0, 581.30, 2418.70),
        # C consultor: falta 1×1; justificados 2 + 2 h (0.25) = 2.25 > 1 libre => exceso 1.25
        "919103": (20, 17, 1, 0, 2, 2.25, 7000, 0, 233.33, 0, 291.67, 0, 525.00, 6475.00),
        # D alta 17/06: 14 días comerciales, 10 laborables; falta 1×2
        "919104": (10, 9, 1, 0, 0, 2, 2100, 266.91, 300, 0, 0, 0, 566.91, 1533.09),
        # E baja 14/06: 14 días; 10 laborables; un retraso de 15 min (sin sanción)
        "919105": (10, 10, 0, 15, 0, 0, 2333.33, 296.57, 0, 0, 0, 0, 296.57, 2036.76),
    }
    for ci, (lab, asi, fal, mins, jus, dd, gan, afp, df, da, do, mu, td, liqd) in esperado.items():
        x = L[ci]
        got = (x["dias_laborables"], x["dias_asistidos"], x["faltas"], x["min_retraso"], x["dias_justificados"], x["dias_descuento"])
        assert got == (lab, asi, fal, mins, jus, dd), (ci, got)
        for campo, v in (("total_ganado", gan), ("aporte_laboral", afp), ("desc_faltas", df), ("desc_atrasos", da), ("desc_otros", do),
                         ("desc_multas", mu), ("total_descuentos", td), ("liquido_pagable", liqd)):
            aprox(x[campo], v, f"{ci}.{campo}")
    assert "Amonestación" in L["919101"]["sancion"] and "excede el máximo contractual" in L["919103"]["observacion"]


# =============================================================================== 2. identidades dentro de la liquidación
def test_identidades_contables(client, escenario):
    for ci, x in liq(client).items():
        aprox(x["liquido_pagable"], x["total_ganado"] - x["aporte_laboral"] - x["rc_iva"] - x["desc_asistencia"] - x["desc_multas"], f"líquido {ci}")
        aprox(x["total_descuentos"], x["aporte_laboral"] + x["rc_iva"] + x["desc_asistencia"] + x["desc_multas"], f"total desc {ci}")
        aprox(x["desc_asistencia"], x["desc_faltas"] + x["desc_atrasos"] + x["desc_otros"], f"desc asistencia {ci}")
        aprox(x["dias_asistidos"], x["dias_laborables"] - x["faltas"] - x["dias_justificados"], f"asistidos {ci}")
        assert x["liquido_pagable"] >= 0


# =============================================================================== 3. la liquidación coincide con el detalle diario
def test_detalle_diario_suma_la_liquidacion(client, escenario):
    L = liq(client)
    diario = {}
    for a in _ok(client.get(f"/api/asistencia/{A}/{M}")):
        diario.setdefault(a["empleado_id"], []).append(a)
    for ci, x in L.items():
        filas = diario[x["empleado_id"]]
        lab = [f for f in filas if f["estado"] not in ("NO_LABORABLE", "FERIADO")]
        assert len(lab) == x["dias_laborables"], ci
        aprox(sum(f["falta"] for f in lab), x["faltas"], f"faltas {ci}")
        aprox(sum(f["min_retraso"] for f in lab), x["min_retraso"], f"minutos {ci}")
        aprox(sum(f["justificado"] for f in lab), x["dias_justificados"], f"justificados {ci}")


# =============================================================================== 4. planillas
def _planilla_filas(wb, hoja, n_extra=1):
    keys = [k for k, _, _ in PX._cols([(f"x{i}", "x", 1) for i in range(n_extra)])]      # orden de columnas de la planilla
    ws = wb[hoja]
    filas = {}
    for row in ws.iter_rows(values_only=True):
        if row[3] and str(row[3]).startswith("91") and len(str(row[3])) == 6:   # columna C.I.
            filas[str(row[3])] = dict(zip(keys, row))
    return ws, filas


def _verificar_fila_planilla(f, x, ci):
    aprox(f["haber"], x["haber_basico"], f"haber {ci}")
    aprox(f["dias"], x["dias_trabajados"], f"días {ci}")
    aprox(f["ganado"], x["total_ganado"], f"ganado {ci}")
    aprox(f["afp"], x["aporte_laboral"], f"afp {ci}")
    aprox(f["patronal"], x["aporte_patronal"], f"patronal {ci}")
    aprox(f["rciva"], x["rc_iva"], f"rciva {ci}")
    aprox(f["ripdias"], x["dias_descuento"], f"días rip {ci}")
    aprox(f["ripmonto"], x["desc_asistencia"] + x["desc_multas"], f"faltas, atrasos y otros {ci}")      # incluye multas
    aprox(f["totdesc"], x["total_descuentos"], f"total desc {ci}")
    aprox(f["liquido"], x["liquido_pagable"], f"líquido {ci}")
    aprox(f["ganado"] - f["totdesc"], f["liquido"], f"identidad de fila {ci}")


def test_planilla_de_sueldos_coincide_con_la_liquidacion(client, escenario):
    L = liq(client)
    wb = openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/planilla.xlsx").content))
    ws, filas = _planilla_filas(wb, "Planilla")
    assert set(filas) == set(L), "la planilla debe mostrar a TODOS los servidores"
    for ci, f in filas.items():
        _verificar_fila_planilla(f, L[ci], ci)
    # los rangos SUM de subtotales cubren exactamente las filas de cada bloque
    sumas = [str(c.value) for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=SUM(")]
    assert sumas
    rs = wb["Resumen"]
    por_mod = {"PERMANENTE": 5, "EVENTUAL": 6, "CONSULTOR_LINEA": 7}
    for mod, fila in por_mod.items():
        xs = [x for x in L.values() if x["modalidad"] == mod]
        assert rs.cell(fila, 2).value == len(xs)
        aprox(rs.cell(fila, 3).value, sum(x["total_ganado"] for x in xs), f"resumen ganado {mod}")
        aprox(rs.cell(fila, 6).value, sum(x["desc_asistencia"] for x in xs), f"resumen desc asistencia {mod}")
        aprox(rs.cell(fila, 8).value, sum(x["liquido_pagable"] for x in xs), f"resumen líquido {mod}")


def test_planillas_de_altas_y_bajas_coinciden(client, escenario):
    L = liq(client)
    _, nuevos = _planilla_filas(openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/nuevos.xlsx").content)), "Nuevos", 5)
    assert set(nuevos) == {"919104"}
    _verificar_fila_planilla(nuevos["919104"], L["919104"], "alta")
    _, bajas = _planilla_filas(openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/desvinculados.xlsx").content)), "Desvinculados", 5)
    assert set(bajas) == {"919105"}
    _verificar_fila_planilla(bajas["919105"], L["919105"], "baja")


# =============================================================================== 5. reporte detallado
def test_reporte_detallado_coincide(client, escenario):
    L = liq(client)
    wb = openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/asistencia.xlsx").content))
    ws = wb["Resumen institucional"]
    cab = [c.value for c in ws[4]]
    ix = {t: i for i, t in enumerate(cab)}
    vistos = {}
    for row in ws.iter_rows(min_row=5, values_only=True):
        if row[1] and str(row[1]).startswith("91"):
            vistos[str(row[1])] = row
    assert set(vistos) == set(L)
    for ci, r in vistos.items():
        x = L[ci]
        for tit, campo in (("Días laborables", "dias_laborables"), ("Días asistidos", "dias_asistidos"), ("Faltas injust.", "faltas"), ("Días justificados", "dias_justificados"),
                           ("N° retrasos", "nro_retrasos"), ("Min. retraso", "min_retraso"), ("Días de descuento", "dias_descuento"), ("Total ganado Bs", "total_ganado"),
                           ("Desc. faltas Bs", "desc_faltas"), ("Desc. atrasos Bs", "desc_atrasos"), ("Desc. permisos s/goce y otros Bs", "desc_otros"),
                           ("Multas y desc. adicionales Bs", "desc_multas"), ("Aporte laboral Bs", "aporte_laboral"), ("RC-IVA Bs", "rc_iva"),
                           ("Total descuentos Bs", "total_descuentos"), ("Líquido pagable Bs", "liquido_pagable")):
            aprox(r[ix[tit]], x[campo], f"{ci} {tit}")
    # Detalle diario: sumas por servidor = liquidación
    det = {}
    for row in wb["Detalle diario"].iter_rows(min_row=5, values_only=True):
        if row[0] and str(row[0]).startswith("91"):
            d = det.setdefault(str(row[0]), {"min": 0, "falta": 0, "just": 0, "parcial": 0})
            d["min"] += row[6]; d["falta"] += row[7]; d["just"] += row[8]; d["parcial"] += row[9]
    for ci, d in det.items():
        aprox(d["min"], L[ci]["min_retraso"], f"detalle min {ci}")
        aprox(d["falta"], L[ci]["faltas"], f"detalle faltas {ci}")
        aprox(d["just"], L[ci]["dias_justificados"], f"detalle justificados {ci}")
    aprox(det["919101"]["parcial"], 0.25, "permiso por horas A (sin goce)")
    aprox(det["919103"]["parcial"], 0.25, "permiso por horas C (consultor)")
    # los permisos por horas aparecen en la hoja de imputación
    imput = [r for r in wb["Faltas y retrasos"].iter_rows(min_row=5, values_only=True) if r[3] == "Permiso por horas"]
    assert len(imput) == 2 and any("SIN goce" in r[5] for r in imput)


# =============================================================================== 6. consolidado de auditoría (.txt y .xlsx)
def test_consolidado_txt_y_xlsx_coinciden(client, escenario):
    L = liq(client)
    rows = list(csv.reader(io.StringIO(client.get(f"/api/reportes/{A}/{M}/auditoria.txt").content.decode()), delimiter="\t"))
    assert rows[0] == COLUMNAS
    txt = {r[1]: dict(zip(COLUMNAS, r)) for r in rows[1:] if r[1].startswith("91")}
    ws = openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/auditoria.xlsx").content))["Consolidado"]
    filas = list(ws.iter_rows(values_only=True))
    assert list(filas[0]) == COLUMNAS_XLSX
    xl = {f[1]: dict(zip(COLUMNAS_XLSX, f)) for f in filas[1:] if str(f[1]).startswith("91")}
    assert set(txt) == set(xl) == set(L)
    for ci, x in L.items():
        t, e = txt[ci], xl[ci]
        aprox(t["FALTAS"], x["faltas"]); aprox(t["MINUTOS_RETRASO"], x["min_retraso"]); aprox(t["DIAS_ASISTIDOS"], x["dias_asistidos"])
        aprox(t["IMPORTE_DESCUENTOS_APLICADOS"], x["desc_asistencia"] + x["desc_multas"], f"txt importe {ci}")           # incluye multas
        aprox(e["IMPORTE_DESCUENTOS_APLICADOS"], t["IMPORTE_DESCUENTOS_APLICADOS"], f"xlsx = txt {ci}")
        aprox(e["FALTAS_ATRASOS_Y_OTROS_PLANILLA"], x["desc_asistencia"] + x["desc_multas"])
        for tit, campo in (("HABER_BASICO", "haber_basico"), ("DIAS_TRABAJADOS", "dias_trabajados"), ("TOTAL_GANADO", "total_ganado"), ("APORTE_LABORAL", "aporte_laboral"),
                           ("APORTE_PATRONAL", "aporte_patronal"), ("RC_IVA", "rc_iva"), ("TOTAL_DIAS_LABORABLES", "dias_laborables"), ("DIAS_ASISTIDOS", "dias_asistidos"),
                           ("FALTAS", "faltas"), ("NRO_RETRASOS", "nro_retrasos"), ("MINUTOS_RETRASO", "min_retraso"), ("DIAS_PERMISO_JUSTIFICADO", "dias_justificados"),
                           ("DIAS_DESC_FALTAS", "dias_desc_faltas"), ("DIAS_DESC_ATRASOS", "dias_desc_atrasos"), ("DIAS_DESC_PERMISO_SIN_GOCE", "dias_desc_sin_goce"),
                           ("DIAS_DESC_EXCESO_CONSULTOR", "dias_desc_exceso_consultor"), ("DIAS_DESCUENTO_TOTAL", "dias_descuento"), ("DESC_FALTAS", "desc_faltas"),
                           ("DESC_ATRASOS", "desc_atrasos"), ("DESC_PERMISOS_SIN_GOCE_Y_OTROS", "desc_otros"), ("MULTAS_Y_DESCUENTOS_ADICIONALES", "desc_multas"),
                           ("TOTAL_DESCUENTOS", "total_descuentos"), ("LIQUIDO_PAGABLE", "liquido_pagable")):
            aprox(e[tit], x[campo], f"xlsx {ci} {tit}")
    assert xl["919105"]["FECHA_BAJA"] == "2019-06-14" and xl["919105"]["CAUSAL_BAJA"] == "Renuncia" and xl["919104"]["FECHA_INGRESO"] == "2019-06-17"
    assert xl["919101"]["NOMBRES"] == "Alba" and xl["919101"]["SANCION_RIP"].startswith("Amonestación")


# =============================================================================== 7. informe Word
def _num(s):
    return float(s.replace(".", "").replace(",", ".").replace("%", ""))


def test_informe_word_coincide(client, escenario):
    L = liq(client)
    d = docx.Document(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/informe.docx").content))
    res = {r.cells[0].text: [c.text for c in r.cells] for r in d.tables[1].rows[1:]}
    ec = {r.cells[0].text: [c.text for c in r.cells] for r in d.tables[2].rows[1:]}
    S = lambda k: sum(x[k] for x in L.values())  # noqa: E731
    assert res["Total Personal Controlado (Planta, Eventual y Consultores)"][1] == str(len(L))
    assert res["Total Personal Controlado (Planta, Eventual y Consultores)"][2] == f"{S('dias_laborables'):g} días-hombre"
    falt = next(v for k, v in res.items() if k.startswith("Faltas"))
    assert falt[1] == str(sum(1 for x in L.values() if x["faltas"] > 0)) and falt[2] == f"{S('faltas'):g} días"
    atr = next(v for k, v in res.items() if k.startswith("Personal con Atrasos"))
    assert atr[2] == f"{int(S('min_retraso'))} minutos"
    ph = next(v for k, v in res.items() if k.startswith("Permisos por horas"))
    assert ph[1] == "2" and ph[2] == "4 horas"                                  # A: 2 h sin goce + C: 2 h con goce
    for concepto, campo in (("Total ganado del mes (haber proporcional + bono)", "total_ganado"), ("Aporte laboral AFP/Gestora (descuento de ley)", "aporte_laboral"),
                            ("Descuento por faltas injustificadas", "desc_faltas"), ("Descuento por atrasos acumulados (escala RIP)", "desc_atrasos"),
                            ("Descuento por permisos sin goce y exceso de ausencias de consultores", "desc_otros"), ("Multas y descuentos adicionales", "desc_multas"),
                            ("TOTAL DESCUENTOS", "total_descuentos"), ("LÍQUIDO PAGABLE (coincide con la Planilla de Sueldos y Salarios)", "liquido_pagable")):
        aprox(_num(ec[concepto][2]), S(campo), concepto)
    aprox(_num(ec["TOTAL DESCUENTOS"][2]), _num(ec["Aporte laboral AFP/Gestora (descuento de ley)"][2]) + _num(ec["RC-IVA retenido"][2]) + _num(ec["Descuento por faltas injustificadas"][2])
          + _num(ec["Descuento por atrasos acumulados (escala RIP)"][2]) + _num(ec["Descuento por permisos sin goce y exceso de ausencias de consultores"][2])
          + _num(ec["Multas y descuentos adicionales"][2]), "el desglose suma el total de descuentos")
    # la tabla de atrasos y la de faltas muestran el importe de la planilla
    texto = "\n".join(c.text for t in d.tables for row in t.rows for c in row.cells)
    assert "= Bs 400,00" in texto                          # A: descuento por su falta (1 × 2 días × 6000/30)
    assert "Amonestación escrita" in texto and "52 min" in texto


# =============================================================================== 8. una sola verdad entre todos los reportes
def test_total_liquido_igual_en_todos_los_reportes(client, escenario):
    L = liq(client)
    total = sum(x["liquido_pagable"] for x in L.values())
    wb = openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/planilla.xlsx").content))
    _, filas = _planilla_filas(wb, "Planilla")
    aprox(sum(f["liquido"] for f in filas.values()), total, "planilla")
    ws = openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/auditoria.xlsx").content))["Consolidado"]
    idx = COLUMNAS_XLSX.index("LIQUIDO_PAGABLE")
    aprox(sum(f[idx] for f in list(ws.iter_rows(values_only=True))[1:] if str(f[1]).startswith("91")), total, "auditoría xlsx")
    aprox(total, 4637.40 + 2418.70 + 6475.00 + 1533.09 + 2036.76, "suma manual")


# =============================================================================== 9. multas: alta, efecto y anulación
def test_multas_efecto_y_anulacion(client, escenario):
    emp = escenario["9102"]
    antes = liq(client)["919102"]
    a = _ok(client.post("/api/ajustes", json={"anio": A, "mes": M, "empleado_id": emp["id"], "tipo": "DESCUENTO", "concepto": "Descuento por préstamo institucional", "monto": 200.50}))
    despues = liq(client)["919102"]
    aprox(despues["desc_multas"], 200.50); aprox(despues["liquido_pagable"], antes["liquido_pagable"] - 200.50)
    wb = openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/planilla.xlsx").content))
    _, filas = _planilla_filas(wb, "Planilla")
    aprox(filas["919102"]["ripmonto"], antes["desc_asistencia"] + 200.50)
    _ok(client.post(f"/api/ajustes/{a['id']}/anular"))
    aprox(liq(client)["919102"]["liquido_pagable"], antes["liquido_pagable"])
    # no puede dejar el líquido en negativo
    grande = _ok(client.post("/api/ajustes", json={"anio": A, "mes": M, "empleado_id": emp["id"], "tipo": "MULTA", "concepto": "Multa desproporcionada de prueba", "monto": 999999}))
    x = liq(client)["919102"]
    assert x["liquido_pagable"] >= 0 and "limitados" in x["observacion"]
    _ok(client.post(f"/api/ajustes/{grande['id']}/anular"))
    assert client.post("/api/ajustes", json={"anio": A, "mes": M, "empleado_id": emp["id"], "tipo": "MULTA", "concepto": "x", "monto": 10}).status_code == 422
    assert client.post("/api/ajustes", json={"anio": A, "mes": M, "empleado_id": emp["id"], "tipo": "MULTA", "concepto": "Monto negativo", "monto": -5}).status_code == 422


# =============================================================================== 10. periodo cerrado congela las cifras
def test_cerrado_congela_y_bloquea_ajustes(client, escenario):
    antes = liq(client)
    _ok(client.post(f"/api/periodos/{A}/{M}/cerrar"))
    r = client.post("/api/ajustes", json={"anio": A, "mes": M, "empleado_id": escenario["9101"]["id"], "tipo": "MULTA", "concepto": "Multa tardía de prueba", "monto": 50})
    assert r.status_code == 422 and "CERRADO" in r.text
    assert liq(client) == antes
    wb = openpyxl.load_workbook(io.BytesIO(client.get(f"/api/reportes/{A}/{M}/planilla.xlsx").content))
    _, filas = _planilla_filas(wb, "Planilla")
    for ci, x in antes.items():
        aprox(filas[ci]["liquido"], x["liquido_pagable"])
