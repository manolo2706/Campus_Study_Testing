"""Estructura estándar de respuesta definida en el contrato."""
from fastapi.responses import JSONResponse


def exito(datos, mensaje: str, codigo: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=codigo,
        content={"exito": True, "datos": datos, "mensaje": mensaje},
    )


def error(codigo: int, tipo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(
        status_code=codigo,
        content={
            "exito": False,
            "error": {"codigo": codigo, "tipo": tipo, "mensaje": mensaje},
        },
    )
