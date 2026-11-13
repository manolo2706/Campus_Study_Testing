"""Errores del contrato (sección H) con la estructura de respuesta acordada."""


class ErrorContrato(Exception):
    codigo = 500
    tipo = "ERROR_INTERNO"

    def __init__(self, mensaje: str, tipo: str | None = None):
        self.mensaje = mensaje
        if tipo:
            self.tipo = tipo
        super().__init__(mensaje)


class SolicitudIncorrecta(ErrorContrato):
    codigo = 400
    tipo = "SOLICITUD_INCORRECTA"


class NoAutorizado(ErrorContrato):
    codigo = 401
    tipo = "NO_AUTORIZADO"


class NoEncontrado(ErrorContrato):
    codigo = 404
    tipo = "RECURSO_NO_ENCONTRADO"


class ErrorInterno(ErrorContrato):
    codigo = 500
    tipo = "ERROR_INTERNO"


class ServicioNoDisponible(ErrorContrato):
    codigo = 503
    tipo = "SERVICIO_NO_DISPONIBLE"
