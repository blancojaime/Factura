"""Evaluacion de ofertas: Precio Evaluado Mas Bajo con margen de preferencia Pro-Bolivia / MyPE.

Reglas (puras, sin base de datos):
  * Solo se ordenan las ofertas que `cumple_especificaciones` y ademas
    - no exceden el monto referencial (que es el certificado presupuestariamente) y
    - no ofrecen un plazo mayor al solicitado (para que la formalizacion Orden/Contrato no cambie).
  * El margen de preferencia solo se aplica si el proveedor tiene registro valido:
        precio_evaluado = monto * (1 - margen/100)
  * Se recomienda el menor precio evaluado. Ante empate gana la oferta recibida primero
    (fecha/hora de recepcion; si coincide, la que figura antes en la lista).
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

CENTAVOS = Decimal("0.01")


@dataclass
class OfertaIn:
    id: Any
    razon_social: str
    monto: Decimal
    plazo_dias: int
    cumple: bool
    fecha_recepcion: datetime
    margen_pct: Decimal = Decimal("0")
    registro_valido: bool = False


@dataclass
class OfertaEval:
    id: Any
    razon_social: str
    monto: Decimal
    plazo_dias: int
    fecha_recepcion: datetime
    margen_aplicado_pct: Decimal
    precio_evaluado: Decimal | None
    elegible: bool
    motivo: str = ""
    ranking: int | None = None
    recomendada: bool = False
    desempate: bool = False


@dataclass
class ResultadoEvaluacion:
    ofertas: list[OfertaEval] = field(default_factory=list)
    recomendada: OfertaEval | None = None
    hay_desempate: bool = False


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def precio_evaluado(monto: Decimal, margen_pct: Decimal, registro_valido: bool) -> tuple[Decimal, Decimal]:
    """Devuelve (precio_evaluado, margen_aplicado)."""
    margen = Decimal(margen_pct) if registro_valido else Decimal("0")
    return _q(Decimal(monto) * (Decimal("100") - margen) / Decimal("100")), margen


def evaluar(ofertas: list[OfertaIn], monto_referencial: Decimal, plazo_maximo_dias: int) -> ResultadoEvaluacion:
    evaluadas: list[OfertaEval] = []
    for o in ofertas:
        pe, margen = precio_evaluado(o.monto, o.margen_pct, o.registro_valido)
        motivo = ""
        if not o.cumple:
            motivo = "No cumple las especificaciones técnicas"
        elif Decimal(o.monto) > Decimal(monto_referencial):
            motivo = "Excede el monto referencial certificado"
        elif o.plazo_dias > plazo_maximo_dias:
            motivo = f"Plazo ofertado ({o.plazo_dias} días) mayor al solicitado ({plazo_maximo_dias} días)"
        evaluadas.append(OfertaEval(
            id=o.id, razon_social=o.razon_social, monto=_q(Decimal(o.monto)), plazo_dias=o.plazo_dias,
            fecha_recepcion=o.fecha_recepcion, margen_aplicado_pct=margen, precio_evaluado=pe,
            elegible=(motivo == ""), motivo=motivo))

    elegibles = [e for e in evaluadas if e.elegible]
    # orden estable: menor precio evaluado, luego primera recepcion; Python conserva el orden de entrada si empatan
    elegibles.sort(key=lambda e: (e.precio_evaluado, e.fecha_recepcion))
    res = ResultadoEvaluacion(ofertas=evaluadas)
    for pos, e in enumerate(elegibles, start=1):
        e.ranking = pos
    if elegibles:
        mejor = elegibles[0]
        mejor.recomendada = True
        res.recomendada = mejor
        empatadas = [e for e in elegibles if e.precio_evaluado == mejor.precio_evaluado]
        if len(empatadas) > 1:
            res.hay_desempate = True
            mejor.desempate = True
    # presentacion: primero las ordenadas, luego las no elegibles
    res.ofertas = elegibles + [e for e in evaluadas if not e.elegible]
    return res
