"""Enumeraciones del dominio (se guardan como texto con CHECK en la base de datos)."""
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # pragma: no cover
        return self.value


class Rol(StrEnum):
    SOLICITANTE = "ROL_SOLICITANTE"
    PRESUPUESTO = "ROL_PRESUPUESTO"
    CONTRATACIONES = "ROL_CONTRATACIONES"
    RPA = "ROL_RPA"
    RECEPCION = "ROL_RECEPCION"
    ADMIN = "ROL_ADMIN"


class TipoObjeto(StrEnum):
    BIEN = "BIEN"
    SERVICIO_GENERAL = "SERVICIO_GENERAL"
    CONSULTORIA = "CONSULTORIA"
    OBRA = "OBRA"


class MetodoFormalizacion(StrEnum):
    ORDEN_COMPRA = "ORDEN_COMPRA"
    ORDEN_SERVICIO = "ORDEN_SERVICIO"
    CONTRATO = "CONTRATO"


class Estado(StrEnum):
    BORRADOR = "BORRADOR"
    SOLICITADO = "SOLICITADO"
    CERTIFICADO_PRESUPUESTO = "CERTIFICADO_PRESUPUESTO"
    EN_COTIZACION = "EN_COTIZACION"
    EVALUADO = "EVALUADO"
    ADJUDICADO = "ADJUDICADO"
    FORMALIZADO = "FORMALIZADO"
    RECEPCIONADO = "RECEPCIONADO"
    DEVENGADO = "DEVENGADO"
    ANULADO = "ANULADO"


class ModalidadCuantia(StrEnum):
    COMPRA_DIRECTA = "COMPRA_DIRECTA"            # hasta Bs 20.000
    CONSULTA_PRECIOS = "CONSULTA_PRECIOS_SICOES"  # Bs 20.001 a 50.000 (Formulario 110)


class EstadoCHB(StrEnum):
    NO_APLICA = "NO_APLICA"                                  # no es BIEN
    COMPRA_CHB_OBLIGATORIA = "COMPRA_CHB_OBLIGATORIA"        # coincide con el catalogo
    EXCEPCION_INCOMPATIBILIDAD = "EXCEPCION_INCOMPATIBILIDAD"  # coincide pero se compra fuera
    SIN_COINCIDENCIA = "SIN_COINCIDENCIA"                    # no existe en el catalogo


class TipoDoc(StrEnum):
    C1_SOLICITUD = "C1_SOLICITUD"
    INFORME_EXCEPCION_CHB = "INFORME_EXCEPCION_CHB"
    CERTIFICACION_C31 = "CERTIFICACION_C31"
    FICHA_COTIZACION = "FICHA_COTIZACION"
    CUADRO_COMPARATIVO = "CUADRO_COMPARATIVO"
    NOTA_ADJUDICACION = "NOTA_ADJUDICACION"
    ORDEN_COMPRA_SERVICIO = "ORDEN_COMPRA_SERVICIO"
    CONTRATO_ADMINISTRATIVO = "CONTRATO_ADMINISTRATIVO"
    ACTA_RECEPCION_FORM500 = "ACTA_RECEPCION_FORM500"


class EstadoPreventivo(StrEnum):
    ACTIVO = "ACTIVO"
    LIBERADO = "LIBERADO"
    DEVENGADO = "DEVENGADO"


def valores(enum_cls: type[Enum]) -> list[str]:
    return [e.value for e in enum_cls]


def sql_in(columna: str, enum_cls: type[Enum]) -> str:
    """Fragmento CHECK: columna IN ('A','B',...)."""
    lista = ", ".join(f"'{v}'" for v in valores(enum_cls))
    return f"{columna} IN ({lista})"
