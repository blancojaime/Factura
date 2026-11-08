from datetime import datetime

import pytest

from app.services.biometrico import parsear_biometrico, parse_fecha, parse_hora
from conftest import DATOS

ESPERADA = 22 * 4 * 5 - 22 * 4 * 0   # se verifica abajo contra el CSV


def _claves(regs):
    return sorted((r.identificador, r.fecha_hora) for r in regs)


def test_tres_formatos_equivalentes():
    f1, r1, rej1 = parsear_biometrico("a.csv", (DATOS / "biometrico_octubre_2026.csv").read_bytes())
    f2, r2, rej2 = parsear_biometrico("a.dat", (DATOS / "biometrico_octubre_2026.dat").read_bytes())
    f3, r3, rej3 = parsear_biometrico("a.xlsx", (DATOS / "biometrico_octubre_2026.xlsx").read_bytes())
    assert (f1, f2, f3) == ("CSV", "ZK_ATTLOG", "XLSX")
    assert not rej1 and not rej2 and not rej3
    assert _claves(r1) == _claves(r2) == _claves(r3) and len(r1) == 408


def test_cabecera_en_fila_4_y_columna_incidencia_ignorada():
    csv = "ID Empleado;Fecha;Hora;Estado / Incidencia\n1;02/11/2026;08:18:45;Tardanza (18 min)\n"
    _, r, _ = parsear_biometrico("x.csv", csv.encode())
    assert r[0].fecha_hora == datetime(2026, 11, 2, 8, 18, 45) and r[0].tipo_evento == ""


def test_formatos_fecha_hora():
    assert parse_fecha("05/10/2026").month == 10
    assert parse_fecha("2026-10-05").day == 5
    assert parse_fecha("05/10/2026", "mdy").month == 5
    assert parse_hora("8:05").minute == 5 and parse_hora("08:05:09").second == 9
    assert parse_hora("02:30 PM").hour == 14
    with pytest.raises(ValueError):
        parse_fecha("32/13/2026")


def test_filas_invalidas_se_reportan_sin_detener():
    csv = "ID;Fecha;Hora\n1;01/10/2026;08:00\n2;no-es-fecha;08:00\n3;02/10/2026;25:99\n"
    _, r, rej = parsear_biometrico("x.csv", csv.encode())
    assert len(r) == 1 and len(rej) == 2


def test_archivo_sin_columnas_validas():
    from app.services.personal import plantilla_xlsx
    with pytest.raises(ValueError, match="columnas"):
        parsear_biometrico("x.xlsx", plantilla_xlsx())
    with pytest.raises(ValueError, match="Excel"):
        parsear_biometrico("x.xlsx", b"no es un zip")


def test_latin1_y_ids_con_ceros():
    data = "ID;Fecha;Hora;Tipo\n0001;01/10/2026;08:00;Entrada\n".encode("latin-1")
    _, r, _ = parsear_biometrico("x.csv", data)
    assert r[0].identificador == "1"
