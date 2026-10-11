"""Maquina de estados del tramite y permisos por rol.

BORRADOR -> SOLICITADO -> CERTIFICADO_PRESUPUESTO -> EN_COTIZACION -> EVALUADO -> ADJUDICADO
         -> FORMALIZADO -> RECEPCIONADO -> DEVENGADO          (ANULADO desde cualquier estado previo a DEVENGADO)
"""
from ..enums import Estado, Rol
from ..errors import EstadoInvalidoError

# accion -> (estados de origen permitidos, estado destino, roles autorizados)
TRANSICIONES: dict[str, tuple[set[Estado], Estado, set[Rol]]] = {
    "solicitar": ({Estado.BORRADOR}, Estado.SOLICITADO, {Rol.SOLICITANTE}),
    "devolver": ({Estado.SOLICITADO}, Estado.BORRADOR, {Rol.PRESUPUESTO}),
    "certificar": ({Estado.SOLICITADO}, Estado.CERTIFICADO_PRESUPUESTO, {Rol.PRESUPUESTO}),
    "aprobar_inicio": ({Estado.CERTIFICADO_PRESUPUESTO}, Estado.EN_COTIZACION, {Rol.RPA}),
    "evaluar": ({Estado.EN_COTIZACION}, Estado.EVALUADO, {Rol.CONTRATACIONES}),
    "adjudicar": ({Estado.EVALUADO}, Estado.ADJUDICADO, {Rol.RPA}),
    "declarar_desierta": ({Estado.EN_COTIZACION, Estado.EVALUADO}, Estado.ANULADO, {Rol.RPA}),
    "formalizar": ({Estado.ADJUDICADO}, Estado.FORMALIZADO, {Rol.RPA}),
    "recepcionar": ({Estado.FORMALIZADO}, Estado.RECEPCIONADO, {Rol.RECEPCION}),
    "devengar": ({Estado.RECEPCIONADO}, Estado.DEVENGADO, {Rol.PRESUPUESTO}),
    "anular": (
        {Estado.BORRADOR, Estado.SOLICITADO, Estado.CERTIFICADO_PRESUPUESTO, Estado.EN_COTIZACION,
         Estado.EVALUADO, Estado.ADJUDICADO, Estado.FORMALIZADO, Estado.RECEPCIONADO},
        Estado.ANULADO, {Rol.RPA, Rol.SOLICITANTE}),
}

# El solicitante solo puede anular antes de la certificacion presupuestaria
SOLICITANTE_ANULA_EN = {Estado.BORRADOR, Estado.SOLICITADO}

# estados "pendientes de accion" por rol (para el tablero)
PENDIENTES: dict[Rol, set[Estado]] = {
    Rol.SOLICITANTE: {Estado.BORRADOR},
    Rol.PRESUPUESTO: {Estado.SOLICITADO, Estado.RECEPCIONADO},
    Rol.CONTRATACIONES: {Estado.EN_COTIZACION},
    Rol.RPA: {Estado.CERTIFICADO_PRESUPUESTO, Estado.EVALUADO, Estado.ADJUDICADO},
    Rol.RECEPCION: {Estado.FORMALIZADO},
    Rol.ADMIN: set(),
}


def acciones_disponibles(estado: str, rol: str) -> list[str]:
    e, r = Estado(estado), Rol(rol)
    out = []
    for accion, (origenes, _, roles) in TRANSICIONES.items():
        if e in origenes and r in roles:
            if accion == "anular" and r == Rol.SOLICITANTE and e not in SOLICITANTE_ANULA_EN:
                continue
            out.append(accion)
    return out


def aplicar(c, accion: str, rol: str) -> Estado:
    """Valida la transicion y actualiza el estado. Los permisos por rol se validan aqui tambien."""
    origenes, destino, roles = TRANSICIONES[accion]
    estado = Estado(c.estado)
    if Rol(rol) not in roles:
        raise EstadoInvalidoError("Su rol no puede ejecutar esta acción", "ROL_NO_AUTORIZADO")
    if estado not in origenes:
        raise EstadoInvalidoError(
            f"La acción '{accion}' no es válida con la contratación en estado {estado.value}", "ESTADO_INVALIDO")
    if accion == "anular" and Rol(rol) == Rol.SOLICITANTE and estado not in SOLICITANTE_ANULA_EN:
        raise EstadoInvalidoError("El solicitante solo puede anular antes de la certificación presupuestaria",
                                  "ROL_NO_AUTORIZADO")
    c.estado = destino.value
    return destino
