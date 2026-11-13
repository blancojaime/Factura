from __future__ import annotations
from contabol.util import fmt, parse_num


def test_ufv_cinco_decimales():
    assert parse_num("2,50000") == 2.5
    assert parse_num("2,61234") == 2.61234
    assert parse_num("2.61234") == 2.61234
    assert fmt(2.61234, 5) == "2,61234"


def test_formatos_bolivianos():
    assert parse_num("1.234,56") == 1234.56
    assert parse_num("1,234.56") == 1234.56
    assert parse_num("1.000.000,5") == 1000000.5
    assert parse_num("-3,5") == -3.5
    assert parse_num("") == 0.0


def test_calculadora_evalua_expresiones():
    from contabol.ui.calculadora import evaluar
    assert evaluar("(100+50)/3") == 50.0
    assert evaluar("2,5×4") == 10.0 and evaluar("-3+5") == 2.0
    import pytest
    for malo in ("__import__('os')", "2**3", "True+1", "abc"):
        with pytest.raises(Exception):
            evaluar(malo)
