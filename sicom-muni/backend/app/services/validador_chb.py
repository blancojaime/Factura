"""Motor de validacion del Catalogo "Compro Hecho en Bolivia" (D.S. 4505) y excepciones (D.S. 0181).

Para cada item de tipo BIEN se consulta el catalogo por codigo UNSPSC:
  * hay coincidencia y se compra por catalogo -> COMPRA_CHB_OBLIGATORIA (bloquea la solicitud);
  * hay coincidencia pero la unidad fundamenta incompatibilidad -> EXCEPCION_INCOMPATIBILIDAD;
  * no hay coincidencia -> SIN_COINCIDENCIA;
  los dos ultimos exigen justificacion y generan el Informe Tecnico-Legal de excepcion.
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import EstadoCHB, TipoObjeto
from ..errors import ReglaNegocioError
from ..models import CatalogoCHB

MSG_COMPRA_CHB = ("El bien está disponible en el Catálogo Compro Hecho en Bolivia (D.S. 4505): "
                  "debe adquirirse por catálogo o fundamentarse la excepción")


@dataclass
class ResultadoItemCHB:
    estado: EstadoCHB
    coincidencia: CatalogoCHB | None
    requiere_excepcion: bool
    bloquea_solicitud: bool
    mensaje: str


def buscar_catalogo(db: Session, texto: str, limite: int = 20) -> list[CatalogoCHB]:
    texto = (texto or "").strip()
    consulta = select(CatalogoCHB).where(CatalogoCHB.activo.is_(True))
    if texto:
        patron = f"%{texto.lower()}%"
        from sqlalchemy import func, or_
        consulta = consulta.where(or_(CatalogoCHB.codigo_unspsc.like(f"{texto}%"),
                                      func.lower(CatalogoCHB.descripcion_bien).like(patron)))
    return list(db.scalars(consulta.order_by(CatalogoCHB.codigo_unspsc).limit(limite)))


def consultar_codigo(db: Session, codigo_unspsc: str) -> CatalogoCHB | None:
    return db.scalar(select(CatalogoCHB).where(
        CatalogoCHB.codigo_unspsc == (codigo_unspsc or "").strip(), CatalogoCHB.activo.is_(True)))


def evaluar_item(db: Session, tipo_objeto: str, codigo_unspsc: str, fuera_catalogo: bool) -> ResultadoItemCHB:
    if TipoObjeto(tipo_objeto) != TipoObjeto.BIEN:
        return ResultadoItemCHB(EstadoCHB.NO_APLICA, None, False, False, "No aplica: el objeto no es un bien")
    codigo = (codigo_unspsc or "").strip()
    if not codigo:
        raise ReglaNegocioError(
            "Los ítems de tipo BIEN deben llevar código UNSPSC: la consulta al catálogo CHB es obligatoria",
            codigo="CHB_CODIGO_OBLIGATORIO")
    cat = consultar_codigo(db, codigo)
    if cat is not None and not fuera_catalogo:
        return ResultadoItemCHB(EstadoCHB.COMPRA_CHB_OBLIGATORIA, cat, False, True, MSG_COMPRA_CHB)
    if cat is not None:
        return ResultadoItemCHB(
            EstadoCHB.EXCEPCION_INCOMPATIBILIDAD, cat, True, False,
            "Existe en el catálogo CHB; se compra fuera por incompatibilidad: se exige justificación")
    return ResultadoItemCHB(
        EstadoCHB.SIN_COINCIDENCIA, None, True, False,
        "No existe coincidencia en el catálogo CHB: se exige justificación y se emitirá el informe de excepción")


def validar_contratacion_chb(items, justificacion: str | None, min_caracteres: int = 80) -> list[str]:
    """Devuelve la lista de errores que impiden solicitar la contratacion."""
    errores: list[str] = []
    obligatorios = [i for i in items if i.estado_chb == EstadoCHB.COMPRA_CHB_OBLIGATORIA.value]
    for i in obligatorios:
        errores.append(f"Ítem {i.numero} ({i.codigo_unspsc}): {MSG_COMPRA_CHB}")
    necesita = any(i.estado_chb in (EstadoCHB.EXCEPCION_INCOMPATIBILIDAD.value, EstadoCHB.SIN_COINCIDENCIA.value)
                   for i in items)
    if necesita and len((justificacion or "").strip()) < min_caracteres:
        errores.append(
            f"Se requiere la justificación técnico-legal de compra fuera del Catálogo CHB "
            f"(mínimo {min_caracteres} caracteres)")
    return errores


def requiere_excepcion(items) -> bool:
    return any(i.estado_chb in (EstadoCHB.EXCEPCION_INCOMPATIBILIDAD.value, EstadoCHB.SIN_COINCIDENCIA.value)
               for i in items)
