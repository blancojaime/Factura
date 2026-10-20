"""El motor de cálculo reproduce los ejemplos numéricos del Manual de Usuario VSIAF 2.0."""
import datetime as dt

import pytest

from vsiaf_importer.calc import fecha_fin_vida, valuate
from vsiaf_importer.ufv import UfvMissing, load_from_csv, bundled_csv

UFV = load_from_csv(bundled_csv())


def test_ufv_indices_del_manual():
    assert UFV.get(dt.date(2013, 10, 14)) == 1.87194
    assert UFV.get(dt.date(2013, 4, 11)) == 1.82467
    assert UFV.get(dt.date(2011, 8, 29)) == 1.66535
    assert UFV.get(dt.date(2013, 10, 10)) == 1.87054


def test_manual_pag24_sillon_620():
    v = valuate(UFV, 620.00, 0, 10, dt.date(2013, 4, 11), dt.date(2013, 10, 14))
    assert v.factor == 1.025906
    assert v.valor_actualizado == 636.06
    assert v.dias_totales == 187
    assert v.dep_gestion == 32.59
    assert v.valor_neto == 603.47


def test_manual_pag16_sillon_1380():
    v = valuate(UFV, 1380.00, 0, 10, dt.date(2011, 8, 29), dt.date(2013, 10, 10))
    assert v.factor == 1.123211
    assert v.valor_actualizado == 1550.03
    assert v.dias_totales == 774 and v.dias_gestion == 283
    assert v.dep_acumulada == 328.69
    assert v.valor_neto == 1221.34
    assert v.dep_gestion == pytest.approx(120.16, abs=0.03)   # el manual muestra 120.1x


def test_un_dia_de_depreciacion():
    v = valuate(UFV, 5500, 0, 5, dt.date(2013, 10, 10), dt.date(2013, 10, 10))
    assert v.dias_totales == 1 and v.dep_gestion == 3.01


def test_identidades_contables():
    v = valuate(UFV, 25000, 0, 8, dt.date(2011, 6, 15), dt.date(2013, 10, 10))
    assert v.valor_neto == pytest.approx(v.valor_actualizado - v.dep_acumulada, abs=0.005)
    assert v.actualizacion_gestion == pytest.approx(v.valor_actualizado - v.valor_actualizado_ini, abs=0.005)
    assert v.dep_acumulada == pytest.approx(v.dep_acumulada_ini + v.dep_gestion + v.actualizacion_dep, abs=0.011)


def test_fin_de_vida_util_y_tope():
    inc = dt.date(2011, 1, 1)
    assert fecha_fin_vida(inc, 4) == dt.date(2014, 12, 31)
    v = valuate(UFV, 1000, 0, 4, inc, dt.date(2020, 1, 1))
    assert v.dep_acumulada == v.valor_actualizado and v.valor_neto == 0
    assert v.dep_gestion == 0                      # ya no se deprecia en la gestión


def test_grupo_sin_depreciacion_ni_actualizacion():
    v = valuate(UFV, 5000, 0, 0, dt.date(2012, 1, 2), dt.date(2013, 10, 10), depreciar=False, actualizar=False)
    assert v.valor_actualizado == 5000 and v.dep_acumulada == 0 and v.valor_neto == 5000


def test_dep_acumulada_inicial_se_actualiza():
    v = valuate(UFV, 1000, 200, 10, dt.date(2013, 4, 11), dt.date(2013, 10, 14))
    assert v.valor_actualizado == 1025.91
    assert v.dep_acumulada == pytest.approx(round(200 * 1.025906, 2) + 1025.91 * 0.1 * 187 / 365, abs=0.01)


def test_ufv_faltante():
    with pytest.raises(UfvMissing):
        valuate(UFV, 1, 0, 4, dt.date(1980, 1, 1), dt.date(2013, 1, 1))


def test_fecha_anterior_a_incorporacion():
    v = valuate(UFV, 100, 0, 4, dt.date(2013, 10, 14), dt.date(2013, 10, 1))
    assert v.valor_actualizado == 100 and v.dep_acumulada == 0
