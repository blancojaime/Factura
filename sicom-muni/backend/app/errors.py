"""Excepciones de negocio con respuesta HTTP uniforme."""


class ReglaNegocioError(Exception):
    """Una regla normativa o de negocio impide la operacion (HTTP 422)."""

    def __init__(self, mensaje: str, codigo: str = "REGLA_NEGOCIO", errores: list[str] | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.errores = errores or []


class EstadoInvalidoError(Exception):
    """La accion no es valida en el estado actual del tramite (HTTP 409)."""

    def __init__(self, mensaje: str, codigo: str = "ESTADO_INVALIDO"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class NoEncontradoError(Exception):
    def __init__(self, mensaje: str = "Recurso no encontrado"):
        super().__init__(mensaje)
        self.mensaje = mensaje
