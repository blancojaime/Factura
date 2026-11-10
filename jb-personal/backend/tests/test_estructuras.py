"""Adaptación a distintas estructuras de archivo de relojes biométricos."""
import io
import json
from datetime import datetime

import pytest
from openpyxl import Workbook

from app.services.biometrico import analizar, parsear_biometrico, validar_perfil

T1 = datetime(2026, 9, 1, 8, 2, 5)


def _una(nombre, contenido, **kw):
    fmt, regs, rech = parsear_biometrico(nombre, contenido if isinstance(contenido, bytes) else contenido.encode("utf-8"), **kw)
    return regs, rech


@pytest.mark.parametrize("txt", [
    "Employee ID,Name,Authentication Date and Time,Authentication Type\n7,Juan,2026-09-01 08:02:05,Fingerprint\n",     # estilo Hikvision
    "Person ID\tName\tTime\tStatus\n7\tJuan\t2026-09-01 08:02:05\tCheck In\n",                                         # estilo Dahua
    "No;Nombre;Fecha/Hora;Estado\n7;Juan;01/09/2026 08:02:05;Entrada\n",                                              # estilo Anviz/español
    "User ID|Date|Time|Verify Mode\n7|01/09/2026|08:02:05|Face\n",
    "CODIGO;FECHA;HORA\n007;01/09/2026;8:02:05\n",
    "ID,Date/Time\n7,9/1/2026 8:02:05 AM\n",
])
def test_cabeceras_de_distintas_marcas(txt):
    regs, rech = _una("x.csv", txt, orden_fecha="mdy" if "9/1/2026" in txt else "dmy")
    assert not rech and len(regs) == 1 and regs[0].identificador == "7" and regs[0].fecha_hora == T1


def test_zk_attlog_con_espacios_y_fecha_hora_separadas():
    regs, _ = _una("a.txt", "  7  2026-09-01 08:02:05  1  0  0  0\n  7  2026-09-01 12:01:00  1  1  0  0\n")
    assert [r.tipo_evento for r in regs] == ["Entrada", "Salida"] and regs[0].metodo == "Huella Digital"


def test_estructura_ancha_una_fila_por_dia():
    txt = "ID;Fecha;Entrada;Salida Almuerzo;Entrada Tarde;Salida\n7;01/09/2026;08:02;12:01;SIN MARCA;18:35\n7;02/09/2026;07:58;12:00;14:29;18:31\n"
    a = analizar("a.csv", txt.encode())
    assert a["detectado"] and a["perfil"]["estructura"] == "ancho" and len(a["perfil"]["horas"]) == 4
    regs, rech = _una("a.csv", txt)
    assert len(regs) == 7 and not rech                          # "SIN MARCA" se omite sin error
    assert regs[0].fecha_hora == datetime(2026, 9, 1, 8, 2)


def test_excel_con_titulos_y_hoja_resumen_distinta():
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["TOTALES"])
    w2 = wb.create_sheet("Marcaciones")
    w2.append(["REPORTE DEL RELOJ"]); w2.append([]); w2.append(["Emp. No", "Nombre", "Date", "Time", "Terminal"])
    w2.append([7, "Juan", "01/09/2026", "08:02:05", "T1"])
    b = io.BytesIO(); wb.save(b)
    a = analizar("m.xlsx", b.getvalue())
    assert a["hoja"] == "Marcaciones" and a["perfil"]["fila_cabecera"] == 3
    regs, _ = _una("m.xlsx", b.getvalue())
    assert regs[0].identificador == "7" and regs[0].dispositivo == "T1"


def test_perfil_manual_cabeceras_irreconocibles():
    txt = "A|B|C|D\n007|09-01-2026|8:02:05 AM|x\n008|09-01-2026|1:15:00 PM|x\n"
    with pytest.raises(ValueError, match="Analizar estructura"):
        _una("x.csv", txt)                                        # no autodetecta
    perfil = {"delimitador": "|", "fila_cabecera": 1, "orden_fecha": "mdy", "columnas": {"id": 0, "fecha": 1, "hora": 2}}
    regs, rech = _una("x.csv", txt, perfil=perfil)
    assert not rech and [r.fecha_hora.hour for r in regs] == [8, 13] and regs[0].identificador == "7"


def test_perfil_sin_cabecera_y_formato_fechahora_propio():
    txt = "7;20260901-080205\n7;20260901-120000\n"
    perfil = {"delimitador": ";", "fila_cabecera": 0, "formato_fechahora": "%Y%m%d-%H%M%S", "columnas": {"id": 0, "fechahora": 1}}
    regs, _ = _una("x.txt", txt, perfil=perfil)
    assert regs[0].fecha_hora == T1 and len(regs) == 2


def test_validacion_de_perfiles():
    for malo in ({"columnas": {}}, {"columnas": {"id": 0}}, {"columnas": {"id": 0, "fecha": 1}},
                 {"estructura": "ancho", "columnas": {"id": 0, "fecha": 1}}, {"columnas": {"id": -1, "fechahora": 1}},
                 {"orden_fecha": "xx", "columnas": {"id": 0, "fechahora": 1}}):
        with pytest.raises(ValueError):
            validar_perfil(malo)


def test_flujo_api_analizar_probar_guardar_y_reusar(client):
    contenido = "Cod|Dia|Entrada1|Salida1|Entrada2|Salida2\n9001|01/09/2026|08:00|12:00|14:30|18:30\n9001|02/09/2026|08:05|12:01||18:40\n".replace("Cod|Dia", "Zz|Qq")
    f = {"archivo": ("reloj_x.txt", contenido.encode())}
    a = client.post("/api/biometrico/analizar", files=f).json()
    assert a["muestra"][0][0] == "Zz" and not a["detectado"]               # cabeceras desconocidas: requiere mapeo manual
    cfg = {"estructura": "ancho", "delimitador": "|", "fila_cabecera": 1, "orden_fecha": "dmy", "columnas": {"id": 0, "fecha": 1}, "horas": [2, 3, 4, 5]}
    pr = client.post("/api/biometrico/probar", files=f, data={"config": json.dumps(cfg)}).json()
    assert pr["total"] == 7 and pr["rechazadas"] == 0 and pr["ejemplo"][0]["id"] == "9001"
    assert client.post("/api/biometrico/probar", files=f, data={"config": json.dumps({"columnas": {}})}).status_code == 422
    pid = client.post("/api/biometrico/perfiles", json={"nombre": "Reloj X (ancho)", "marca": "Genérica", "config": cfg}).json()["id"]
    assert any(p["id"] == pid for p in client.get("/api/biometrico/perfiles").json())
    r = client.post("/api/biometrico/importar", files=f, data={"perfil_id": pid})
    assert r.status_code == 200 and r.json()["nuevas"] == 7
    # sin perfil el mismo archivo no se puede importar (pero ya fue importado: se informa igual con claridad)
    assert client.post("/api/biometrico/importar", files={"archivo": ("otro.txt", contenido.replace("9001", "9002").encode())}).status_code == 422
    assert client.delete(f"/api/biometrico/perfiles/{pid}").status_code == 200
