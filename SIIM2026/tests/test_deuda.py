"""Verifica la Deuda Tributaria con los ejemplos de los 'Apuntes Tributarios SIIM' (Ministerio de Participación Popular / USAID)."""
from datetime import date
from decimal import Decimal as X

from siim.calc.deuda import DeudaParams, calcular_deuda, dias_mora


def _p(persona="N", modo="SIIM_PDF"):
    return DeudaParams(r=X("0.1082"), persona=persona, modo_df_ufv=modo)


def test_ejemplo1_anterior_2002_componentes():
    d = calcular_deuda(1000, date(2002, 1, 15), date(2005, 4, 21), None, X("1.10293"), _p(), usd_fv=X("6.86"), usd_26=X("7.49"), ufv_26=X("1.00815"))
    assert d.anterior_2002
    assert d.mora == 1192
    assert d.mv == 194
    assert d.to_mv == 1194
    assert d.interes == 515
    assert d.multa_ufv == 110 and d.multa_bs == 121


def test_ejemplo1_juridica_total():
    d = calcular_deuda(1000, date(2002, 1, 15), date(2005, 4, 21), None, X("1.10293"), _p("J"), usd_fv=X("6.86"), usd_26=X("7.49"), ufv_26=X("1.00815"))
    assert d.multa_ufv == 240 and d.multa_bs == 265
    assert d.total == 1974          # coincide con el documento oficial


def test_ejemplo1_natural_total_corregido():
    """El documento oficial indica 1.662 para persona natural, pero 1.194 + 515 + 121 = 1.830 (error aritmético del documento)."""
    d = calcular_deuda(1000, date(2002, 1, 15), date(2005, 4, 21), None, X("1.10293"), _p(), usd_fv=X("6.86"), usd_26=X("7.49"), ufv_26=X("1.00815"))
    assert d.total == d.to_mv + d.interes + d.multa_bs == 1830


def test_ejemplo2_posterior_2002():
    for persona, total in (("N", 1170), ("J", 1315)):
        d = calcular_deuda(1000, date(2004, 12, 31), date(2005, 4, 21), X("1.08593"), X("1.10293"), _p(persona))
        assert d.mora == 111 and d.mv == 16 and d.to_mv == 1016 and d.interes == 34
        assert d.total == total


def test_modo_division_definicion_legal():
    """Con la definición legal TO(UFV)=TO/UFV la multa de persona natural es menor (se documenta la diferencia)."""
    d = calcular_deuda(1000, date(2004, 12, 31), date(2005, 4, 21), X("1.08593"), X("1.10293"), _p("N", "DIVISION"))
    assert d.to_ufv_df == X("920.870")
    assert d.multa_ufv == 92          # 10% de 920,87 UFV


def test_sin_mora_sin_accesorios():
    d = calcular_deuda(500, date(2005, 3, 31), date(2005, 3, 31), X("1.1"), X("1.1"), _p())
    assert d.mora == 0 and d.total == 500


def test_minimos_y_maximos_multa():
    p = _p("J")
    d = calcular_deuda(10_000_000, date(2004, 12, 31), date(2005, 4, 21), X("1.08593"), X("1.10293"), p)
    assert d.multa_ufv == 2400
    d2 = calcular_deuda(100, date(2004, 12, 31), date(2005, 4, 21), X("1.08593"), X("1.10293"), _p("N"))
    assert d2.multa_ufv == 50


def test_dias_mora():
    assert dias_mora(date(2005, 1, 1), date(2005, 1, 2)) == 1
    assert dias_mora(date(2005, 1, 5), date(2005, 1, 1)) == 0
