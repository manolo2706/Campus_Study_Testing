from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import init_db
from app.routers import estadisticas, eventos, salud


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="CampusStudy — Estadísticas",
    description="Recibe eventos de los demás servicios y expone reportes agregados.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validacion_invalida(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"codigo": 400, "mensaje": "Solicitud incorrecta (parámetro inválido)."},
    )


@app.exception_handler(StarletteHTTPException)
async def error_http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"codigo": exc.status_code, "mensaje": str(exc.detail)},
    )


app.include_router(salud.router)
app.include_router(eventos.router)
app.include_router(estadisticas.router)