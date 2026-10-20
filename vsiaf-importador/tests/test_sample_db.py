"""Pruebas de integración contra una instalación REAL del VSIAF (opcional).

Defina la variable de entorno VSIAF_SAMPLE_DIR con la carpeta que contiene ``dbfs`` (p. ej. la
descomprimida de vsiaf.rar).  Se trabaja siempre sobre una copia.
"""
import datetime as dt
import os
import shutil

import pytest

SAMPLE = os.environ.get("VSIAF_SAMPLE_DIR")
pytestmark = pytest.mark.skipif(not SAMPLE, reason="defina VSIAF_SAMPLE_DIR para ejecutar")


@pytest.fixture()
def copy(tmp_path):
    dst = str(tmp_path / "vsiaf")
    shutil.copytree(SAMPLE, dst)
    return dst


def test_ufv_embebidas_en_tipocambio_app(copy):
    from vsiaf_importer.ufv import load_ufv
    u = load_ufv(copy)
    assert u.source.lower().endswith("tipocambio.app")
    assert u.get(dt.date(2013, 10, 14)) == 1.87194


def test_el_motor_reproduce_las_instantaneas_guardadas_por_vsiaf(copy):
    """REVAL y BAJAS de ejemplo del VSIAF (generadas por el sistema original)."""
    from vsiaf_importer.calc import valuate
    from vsiaf_importer.ufv import load_ufv
    from vsiaf_importer.vsiafdb import VsiafDb
    db = VsiafDb(copy)
    u = load_ufv(copy)
    for r in db.table("BAJAS").records():
        v = valuate(u, r["COSTO"], 0, r["VIDAUTIL"], dt.date(r["ANO"], r["MES"], r["DIA"]),
                    dt.date(r["A_BAJA"], r["M_BAJA"], r["D_BAJA"]))
        assert v.dep_gestion == r["DEPGESTION"]
        assert v.snap_depacu == r["DEPACU"] and v.snap_actua == r["ACTUA"]
        assert (v.valor_actualizado_ini, v.dep_acumulada_ini, v.valor_actualizado, v.actualizacion_dep) == (
            r["COSBAJINI"], r["COSDAINI"], r["COSACTBAJ"], r["ACTDABAJ"])
    for r in db.table("REVAL").records():
        v = valuate(u, r["COSTO"], r["DEPACU_ANT"], r["VIDAUTIL"], dt.date(r["ANO"], r["MES"], r["DIA"]),
                    dt.date(r["A_REVAL"], r["M_REVAL"], r["D_REVAL"]))
        assert (v.dep_gestion, v.snap_depacu, v.snap_actua) == (r["DEPGESTION"], r["DEPACU"], r["ACTUA"])


def test_importacion_sobre_copia_de_la_bd_real(copy, tmp_path):
    from vsiaf_importer import service
    from vsiaf_importer.importer import Options
    from vsiaf_importer.vsiafdb import VsiafDb
    x = str(tmp_path / "libro.xlsx")
    service.create_template(x, copy, ejemplos=True)
    res, _ = service.run(copy, x, Options(default_unit="901"), apply=True)
    assert res.errors == 0 and res.applied
    db = VsiafDb(copy)
    codes = {r["CODIGO"] for r in db.table("ACTUAL").records()}
    assert {"EJ-0001", "EJ-0003", "01-02-3.12-001"} <= codes          # los originales siguen ahí
