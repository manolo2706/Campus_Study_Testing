"""Guarda el identificador de la petición y el token del estudiante durante su
recorrido por el servicio, para poder reenviarlos a los otros microservicios.

Se usa contextvars y no una variable global porque el servicio atiende varias
peticiones al mismo tiempo y cada una debe conservar sus propios datos.
"""
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_token: ContextVar[str] = ContextVar("token", default="")


def fijar_request_id(valor: str) -> None:
    _request_id.set(valor)


def request_id() -> str:
    return _request_id.get()


def fijar_token(valor: str) -> None:
    _token.set(valor or "")


def token() -> str:
    return _token.get()
