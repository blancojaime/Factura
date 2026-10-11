"""Importacion desde Excel: presupuesto por apertura programatica, Catalogo CHB (reemplazo por codigo) y objetivos POA."""
import io
from datetime import date
from decimal import Decimal

from openpyxl import Workbook
from sqlalchemy import select

from app.models import CatalogoCHB, ObjetivoPOA, PartidaPresupuestaria
from tests.helpers import Flujo

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
GESTION = date.today().year


def xlsx(filas, hoja="Hoja1", previas=()):
    wb = Workbook()
    ws = wb.active
    ws.title = hoja
    for f in previas:  # filas de titulo antes del encabezado
        ws.append(f)
    for f in filas:
        ws.append(f)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def subir(client, tokens, usuario, ruta, contenido, nombre="datos.xlsx", esperado=200):
    r = client.post(f"/api/v1{ruta}", headers=tokens[usuario], files={"archivo": (nombre, contenido, XLSX)})
    assert r.status_code == esperado, r.text[:500]
    return r.json()


ENC_PRES = ["Código apertura programática", "Descripción apertura", "Partida", "Fuente", "Organismo", "Presupuesto", "Ejecutado", "Saldo"]


def test_presupuesto_validar_y_confirmar(client, tokens, SessionTest):
    datos = xlsx([
        ENC_PRES,
        ["010-0000-001", "ADMINISTRACION CENTRAL", "31110", "20", "230", 10000, 2500.5, 7499.5],
        [None, None, "31120", "20", "230", "1.500,00", "0,00", "1.500,00"],        # apertura heredada y numeros con coma
        ["010-0000-001", "ADMINISTRACION CENTRAL", "52100", "20", "230", 500, 0, 500],  # fuera de 1xxxx-4xxxx: se omite
        ["TOTAL", None, None, None, None, 12000, 2500.5, 9499.5],
    ], hoja="Presupuesto", previas=[["Ejecución presupuestaria"], []])
    previa = subir(client, tokens, "presupuesto", f"/partidas/importar?gestion={GESTION}", datos)
    assert previa["aplicado"] is False and previa["nuevas"] == 2 and previa["omitidas"] == 1 and not previa["errores"]
    with SessionTest() as s:  # la vista previa no escribe
        assert s.scalar(select(PartidaPresupuestaria).where(PartidaPresupuestaria.codigo_partida == "31110")) is None
    res = subir(client, tokens, "presupuesto", f"/partidas/importar?gestion={GESTION}&confirmar=true", datos)
    assert res["aplicado"] is True and res["nuevas"] == 2
    with SessionTest() as s:
        p = s.scalar(select(PartidaPresupuestaria).where(PartidaPresupuestaria.codigo_partida == "31110"))
        assert (p.programa, p.proyecto, p.actividad, p.fuente, p.organismo) == ("010", "0000", "001", "20", "230")
        assert p.descripcion_apertura == "ADMINISTRACION CENTRAL" and p.monto_ejecutado == Decimal("2500.50")
        assert p.monto_aprobado == Decimal("10000.00") and p.saldo_disponible == Decimal("7499.50")
        q = s.scalar(select(PartidaPresupuestaria).where(PartidaPresupuestaria.codigo_partida == "31120"))
        assert q.saldo_disponible == Decimal("1500.00") and q.descripcion_apertura == "ADMINISTRACION CENTRAL"
    # reimportar actualiza (no duplica)
    datos2 = xlsx([ENC_PRES, ["010-0000-001", "ADMINISTRACION CENTRAL", "31110", "20", "230", 12000, 4000, 8000]], hoja="Presupuesto")
    res = subir(client, tokens, "presupuesto", f"/partidas/importar?gestion={GESTION}&confirmar=true", datos2)
    assert res["actualizadas"] == 1 and res["nuevas"] == 0
    with SessionTest() as s:
        assert len(list(s.scalars(select(PartidaPresupuestaria).where(PartidaPresupuestaria.codigo_partida == "31110")))) == 1
        assert s.scalar(select(PartidaPresupuestaria).where(PartidaPresupuestaria.codigo_partida == "31110")).saldo_disponible == Decimal("8000.00")


def test_presupuesto_errores_no_guardan_nada(client, tokens, SessionTest):
    datos = xlsx([ENC_PRES,
                  ["010-0000-001", "A", "31110", "20", "230", 1000, 0, 1000],
                  ["0100000", "B", "31120", "20", "230", 1000, 0, 1000],     # apertura sin 3 partes
                  ["010-0000-001", "A", "3112", "20", "230", 1000, 0, 1000],  # partida de 4 digitos
                  ["010-0000-001", "A", "31130", "20", "230", 1000, 0, -5]])  # saldo negativo
    previa = subir(client, tokens, "presupuesto", "/partidas/importar", datos)
    assert [e["fila"] for e in previa["errores"]] == [3, 4, 5]
    r = client.post(f"/api/v1/partidas/importar?confirmar=true", headers=tokens["presupuesto"], files={"archivo": ("x.xlsx", datos, XLSX)})
    assert r.status_code == 422 and r.json()["detail"]["codigo"] == "IMPORTACION_CON_ERRORES"
    with SessionTest() as s:
        assert s.scalar(select(PartidaPresupuestaria).where(PartidaPresupuestaria.codigo_partida == "31110")) is None


def test_importar_exige_rol_y_formato(client, tokens):
    datos = xlsx([ENC_PRES, ["010-0000-001", "A", "31110", "20", "230", 1, 0, 1]])
    subir(client, tokens, "solicitante", "/partidas/importar", datos, esperado=403)
    subir(client, tokens, "contrataciones", "/partidas/importar", datos, esperado=403)
    r = subir(client, tokens, "presupuesto", "/partidas/importar", b"no es excel", nombre="a.xlsx", esperado=422)
    assert r["detail"]["codigo"] == "ARCHIVO_INVALIDO"
    r = subir(client, tokens, "presupuesto", "/partidas/importar", datos, nombre="a.xls", esperado=422)
    assert "xlsx" in r["detail"]["mensaje"]
    r = subir(client, tokens, "presupuesto", "/partidas/importar", xlsx([["a", "b"], [1, 2]]), esperado=422)
    assert r["detail"]["codigo"] == "ENCABEZADOS_NO_ENCONTRADOS"


def test_catalogo_chb_reemplaza_codigos_repetidos(client, tokens, SessionTest):
    datos = xlsx([["Código UNSPSC", "Descripción código", "Precio"],
                  [30111505, "Cemento portland IP-30 NUEVO", "65,50"],  # existe en los datos demo: se reemplaza
                  ["31161500", "Tornillos de acero", 1.25],
                  ["1234", "Codigo corto", 5]])
    previa = subir(client, tokens, "contrataciones", "/catalogo-chb/importar", datos)
    assert previa["nuevas"] == 1 and previa["actualizadas"] == 1 and len(previa["errores"]) == 1
    sin_error = xlsx([["Código UNSPSC", "Descripción código", "Precio"], [30111505, "Cemento portland IP-30 NUEVO", "65,50"],
                      ["31161500", "Tornillos de acero", 1.25]])
    res = subir(client, tokens, "contrataciones", "/catalogo-chb/importar?confirmar=true", sin_error)
    assert res["aplicado"] and res["nuevas"] == 1 and res["actualizadas"] == 1
    with SessionTest() as s:
        c = s.scalar(select(CatalogoCHB).where(CatalogoCHB.codigo_unspsc == "30111505"))
        assert c.descripcion_bien == "Cemento portland IP-30 NUEVO" and c.precio_referencial_nacional == Decimal("65.50")
        assert c.fecha_registro == date.today()
        assert len(list(s.scalars(select(CatalogoCHB).where(CatalogoCHB.codigo_unspsc == "30111505")))) == 1
        assert s.scalar(select(CatalogoCHB).where(CatalogoCHB.codigo_unspsc == "31161500")).fecha_registro == date.today()
    # el precio cambia en la siguiente importacion y los demas codigos se conservan
    res = subir(client, tokens, "contrataciones", "/catalogo-chb/importar?confirmar=true",
                xlsx([["Código UNSPSC", "Descripción código", "Precio"], ["31161500", "Tornillos de acero", 1.9]]))
    assert res["actualizadas"] == 1
    with SessionTest() as s:
        assert s.scalar(select(CatalogoCHB).where(CatalogoCHB.codigo_unspsc == "31161500")).precio_referencial_nacional == Decimal("1.90")
        assert s.scalar(select(CatalogoCHB).where(CatalogoCHB.codigo_unspsc == "14111507")) is not None
    subir(client, tokens, "solicitante", "/catalogo-chb/importar", sin_error, esperado=403)


def test_objetivos_poa_importar_y_registrar(client, tokens, SessionTest):
    datos = xlsx([["PROG", "DENOMINACIÓ DEL PROGRAMA", "COD OBJ", "DESCRIPCON OBJETIVO"],  # con los errores de tipeo del Excel original
                  ["0", "FUNCIONAMIENTO ÓRGANO EJECUTIVO", "OBJ1", "Gestionar el funcionamiento del órgano ejecutivo"],
                  ["002", "ADMINISTRACIÓN CENTRAL", "OBJ3", "Garantizar la gestión administrativa eficiente"],
                  ["777", "PROGRAMA NUEVO", "OBJ77", "Objetivo del programa nuevo"]])
    previa = subir(client, tokens, "presupuesto", f"/poa/objetivos/importar?gestion={GESTION}", datos)
    assert previa["total_filas"] == 3 and not previa["errores"] and previa["nuevas"] == 1 and previa["actualizadas"] == 2
    subir(client, tokens, "presupuesto", f"/poa/objetivos/importar?gestion={GESTION}&confirmar=true", datos)
    lista = client.get(f"/api/v1/poa/objetivos?gestion={GESTION}", headers=tokens["solicitante"]).json()
    por_prog = {o["programa"]: o for o in lista}
    assert por_prog["777"]["codigo_objetivo"] == "OBJ77" and por_prog["002"]["descripcion_objetivo"].startswith("Garantizar")
    # '2' y '002' son el mismo programa: el registro manual actualiza, no duplica
    r = client.put("/api/v1/poa/objetivos", headers=tokens["presupuesto"], json={
        "gestion": GESTION, "programa": "2", "denominacion_programa": "ADMINISTRACIÓN CENTRAL", "codigo_objetivo": "OBJ3B",
        "descripcion_objetivo": "Objetivo actualizado manualmente"})
    assert r.status_code == 200
    with SessionTest() as s:
        filas = list(s.scalars(select(ObjetivoPOA).where(ObjetivoPOA.gestion == GESTION, ObjetivoPOA.programa.in_(["2", "002"]))))
        assert len(filas) == 1 and filas[0].codigo_objetivo == "OBJ3B"
    r = client.put("/api/v1/poa/objetivos", headers=tokens["solicitante"], json={
        "gestion": GESTION, "programa": "5", "codigo_objetivo": "X", "descripcion_objetivo": "no autorizado"})
    assert r.status_code == 403


def test_plantillas_descargables(client, tokens):
    for tipo in ("presupuesto", "chb", "poa"):
        r = client.get(f"/api/v1/plantillas/{tipo}", headers=tokens["solicitante"])
        assert r.status_code == 200 and r.content[:2] == b"PK"
    assert client.get("/api/v1/plantillas/otra", headers=tokens["solicitante"]).status_code == 404
