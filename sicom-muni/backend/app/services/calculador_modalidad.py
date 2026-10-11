"""Reglas de cuantia y de formalizacion (puras, sin acceso a base de datos).

Segun la especificacion del proyecto (verificar contra la norma vigente):
  * monto > Bs 50.000            -> se bloquea el proceso (derivar a ANPE).
  * monto <= Bs 20.000           -> compra directa / cotizacion rapida, sin consulta de precios SICOES.
  * Bs 20.000 < monto <= 50.000  -> consulta de precios: se exige el N de Formulario 110 SICOES.
  * plazo <= 15 dias calendario  -> Orden de Compra (bienes) u Orden de Servicio (demas objetos).
  * plazo  > 15 dias calendario  -> Contrato Administrativo (se bloquean las ordenes simples).
"""
from dataclasses import dataclass
from decimal import Decimal

from ..enums import MetodoFormalizacion, ModalidadCuantia, TipoObjeto

TOPE_CONTRATACION_MENOR = Decimal("50000")
TOPE_COMPRA_DIRECTA = Decimal("20000")
PLAZO_ORDEN_MAX_DIAS = 15
MONTO_MINIMO = Decimal("1")

MSG_SUPERA_LIMITE = "El monto supera el límite de Contratación Menor (Bs 50.000). Derive a la modalidad ANPE"


@dataclass(frozen=True)
class ResultadoCuantia:
    modalidad: ModalidadCuantia | None
    requiere_formulario_110: bool
    bloqueado: bool
    mensaje: str


def calcular_modalidad(
    monto: Decimal,
    tope_menor: Decimal = TOPE_CONTRATACION_MENOR,
    tope_directa: Decimal = TOPE_COMPRA_DIRECTA,
) -> ResultadoCuantia:
    monto = Decimal(monto)
    if monto < MONTO_MINIMO:
        return ResultadoCuantia(None, False, True, "El monto debe ser de al menos Bs 1")
    if monto > tope_menor:
        msg = MSG_SUPERA_LIMITE if tope_menor == TOPE_CONTRATACION_MENOR else (
            f"El monto supera el límite de Contratación Menor (Bs {tope_menor:,.0f}). Derive a la modalidad ANPE")
        return ResultadoCuantia(None, False, True, msg)
    if monto <= tope_directa:
        return ResultadoCuantia(
            ModalidadCuantia.COMPRA_DIRECTA, False, False,
            "Compra directa / cotización rápida: no se exige Consulta de Precios SICOES")
    return ResultadoCuantia(
        ModalidadCuantia.CONSULTA_PRECIOS, True, False,
        "Debe publicarse la Consulta de Precios en SICOES y registrarse el número de Formulario 110")


def determinar_formalizacion(
    plazo_dias: int, tipo_objeto: TipoObjeto | str, plazo_max: int = PLAZO_ORDEN_MAX_DIAS
) -> MetodoFormalizacion:
    if plazo_dias < 1:
        raise ValueError("El plazo debe ser de al menos 1 día calendario")
    if plazo_dias > plazo_max:
        return MetodoFormalizacion.CONTRATO
    if TipoObjeto(tipo_objeto) == TipoObjeto.BIEN:
        return MetodoFormalizacion.ORDEN_COMPRA
    return MetodoFormalizacion.ORDEN_SERVICIO
