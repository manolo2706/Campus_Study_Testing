from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.context import get_request_id
from core.envelope import build_error


class ApiError(Exception):
    def __init__(self, status_code: int, message: str, detail: str | None = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(message)


class ServiceUnavailable(ApiError):
    def __init__(self, service: str, detail: str | None = None):
        super().__init__(
            503,
            "Servicio temporalmente no disponible",
            detail or f"el servicio '{service}' no respondio",
        )
        self.service = service


class NotFound(ApiError):
    def __init__(self, message: str, detail: str | None = None):
        super().__init__(404, message, detail)


class BadRequest(ApiError):
    def __init__(self, message: str, detail: str | None = None):
        super().__init__(400, message, detail)


def _json(status_code: int, message: str, detail: str | None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error(status_code, message, detail, get_request_id()),
    )


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return _json(exc.status_code, exc.message, exc.detail)


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _json(exc.status_code, str(exc.detail), None)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    detail = f"campo '{loc}': {first.get('msg', 'invalido')}" if loc else "solicitud invalida"
    return _json(400, "Datos de entrada invalidos", detail)


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return _json(500, "Error interno del servicio", str(exc))
