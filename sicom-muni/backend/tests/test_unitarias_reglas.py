"""Pruebas unitarias de las reglas de negocio puras."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.enums import MetodoFormalizacion, ModalidadCuantia
from app.services.calculador_modalidad import calcular_modalidad, determinar_formalizacion
from app.services.evaluador_ofertas import OfertaIn, evaluar, precio_evaluado
from app.services.numeros_letras import monto_literal

D = Decimal
T0 = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)


# ---------------- limite Bs 50.000 y tramo Bs 20.000
@pytest.mark.parametrize("monto,modalidad,f110,bloqueado", [
    ("1", ModalidadCuantia.COMPRA_DIRECTA, False, False),
    ("18500", ModalidadCuantia.COMPRA_DIRECTA, False, False),
    ("20000", ModalidadCuantia.COMPRA_DIRECTA, False, False),
    ("20000.01", ModalidadCuantia.CONSULTA_PRECIOS, True, False),
    ("32000", ModalidadCuantia.CONSULTA_PRECIOS, True, False),
    ("50000", ModalidadCuantia.CONSULTA_PRECIOS, True, False),
    ("50000.01", None, False, True),
    ("120000", None, False, True),
    ("0.99", None, False, True),
])
def test_cuantia(monto, modalidad, f110, bloqueado):
    r = calcular_modalidad(D(monto))
    assert (r.modalidad, r.requiere_formulario_110, r.bloqueado) == (modalidad, f110, bloqueado)


def test_mensaje_bloqueo_anpe():
    assert calcular_modalidad(D("50000.01")).mensaje == (
        "El monto supera el límite de Contratación Menor (Bs 50.000). Derive a la modalidad ANPE")


# ---------------- regla de los 15 dias
@pytest.mark.parametrize("plazo,tipo,esperado", [
    (1, "BIEN", MetodoFormalizacion.ORDEN_COMPRA),
    (15, "BIEN", MetodoFormalizacion.ORDEN_COMPRA),
    (16, "BIEN", MetodoFormalizacion.CONTRATO),
    (15, "SERVICIO_GENERAL", MetodoFormalizacion.ORDEN_SERVICIO),
    (15, "CONSULTORIA", MetodoFormalizacion.ORDEN_SERVICIO),
    (10, "OBRA", MetodoFormalizacion.ORDEN_SERVICIO),
    (16, "SERVICIO_GENERAL", MetodoFormalizacion.CONTRATO),
    (90, "OBRA", MetodoFormalizacion.CONTRATO),
])
def test_formalizacion_por_plazo(plazo, tipo, esperado):
    assert determinar_formalizacion(plazo, tipo) == esperado


def test_plazo_invalido():
    with pytest.raises(ValueError):
        determinar_formalizacion(0, "BIEN")


# ---------------- evaluacion de ofertas
def oferta(i, monto, cumple=True, plazo=10, min_ago=0, margen="0", valido=False):
    return OfertaIn(id=i, razon_social=f"P{i}", monto=D(monto), plazo_dias=plazo, cumple=cumple,
                    fecha_recepcion=T0 - timedelta(minutes=min_ago), margen_pct=D(margen), registro_valido=valido)


def test_precio_evaluado_mas_bajo_y_orden():
    r = evaluar([oferta(1, "31500"), oferta(2, "29900"), oferta(3, "30500")], D("32000"), 12)
    assert [o.id for o in r.ofertas] == [2, 3, 1]
    assert r.recomendada.id == 2 and [o.ranking for o in r.ofertas] == [1, 2, 3]


def test_excluye_las_que_no_cumplen():
    r = evaluar([oferta(1, "28000", cumple=False), oferta(2, "29000")], D("32000"), 12)
    assert r.recomendada.id == 2
    excluida = next(o for o in r.ofertas if o.id == 1)
    assert not excluida.elegible and excluida.ranking is None and "No cumple" in excluida.motivo


def test_margen_preferencia_solo_con_registro_valido():
    # sin registro valido el margen se ignora; con registro valido cambia el ganador
    sin = evaluar([oferta(1, "30800", margen="5", valido=False), oferta(2, "29900")], D("32000"), 12)
    con = evaluar([oferta(1, "30800", margen="5", valido=True), oferta(2, "29900")], D("32000"), 12)
    assert sin.recomendada.id == 2
    assert con.recomendada.id == 1 and con.ofertas[0].precio_evaluado == D("29260.00")


def test_precio_evaluado_redondeo():
    assert precio_evaluado(D("1000.01"), D("7.5"), True)[0] == D("925.01")
    assert precio_evaluado(D("1000"), D("7.5"), False) == (D("1000.00"), D("0"))


def test_empate_gana_la_primera_recepcion():
    r = evaluar([oferta(1, "1000", min_ago=5), oferta(2, "1000", min_ago=60), oferta(3, "1000", min_ago=30)], D("2000"), 10)
    assert r.recomendada.id == 2 and r.hay_desempate and r.recomendada.desempate
    assert [o.id for o in r.ofertas] == [2, 3, 1]


def test_excede_referencial_y_plazo_no_son_elegibles():
    r = evaluar([oferta(1, "35000"), oferta(2, "30000", plazo=20), oferta(3, "31000")], D("32000"), 12)
    assert r.recomendada.id == 3
    assert {o.id: o.motivo for o in r.ofertas if not o.elegible}.keys() == {1, 2}


def test_sin_elegibles():
    r = evaluar([oferta(1, "10", cumple=False)], D("100"), 5)
    assert r.recomendada is None and not r.hay_desempate


@pytest.mark.parametrize("monto,txt", [
    ("18500", "Son: DIECIOCHO MIL QUINIENTOS 00/100 BOLIVIANOS"),
    ("32000", "Son: TREINTA Y DOS MIL 00/100 BOLIVIANOS"),
    ("21000.50", "Son: VEINTIÚN MIL 50/100 BOLIVIANOS"),
    ("1500000", "Son: UN MILLÓN QUINIENTOS MIL 00/100 BOLIVIANOS"),
    ("100000", "Son: CIEN MIL 00/100 BOLIVIANOS"),
    ("1", "Son: UNO 00/100 BOLIVIANOS"),
])
def test_monto_literal(monto, txt):
    assert monto_literal(monto) == txt
