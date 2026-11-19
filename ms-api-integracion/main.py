from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import settings
from core.context import REQUEST_ID_HEADER, get_request_id, set_request_id
from core.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from events.publisher import event_publisher
from routers import (
    auth,
    estadisticas,
    grupos,
    health,
    match,
    materias,
    notificaciones,
    tareas,
    usuarios,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await event_publisher.iniciar()
    try:
        yield
    finally:
        await event_publisher.detener()


app = FastAPI(
    title=settings.app_name,
    description="Punto unico de entrada, orquestacion y matching de microservicios CampusStudy",
    version=settings.api_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    set_request_id(request.headers.get(REQUEST_ID_HEADER))
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = get_request_id()
    return response


app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

V1 = "/api/v1"
app.include_router(health.router)
app.include_router(health.router, prefix=V1)
app.include_router(auth.router, prefix=V1)
app.include_router(usuarios.router, prefix=V1)
app.include_router(materias.router, prefix=V1)
app.include_router(tareas.router, prefix=V1)
app.include_router(grupos.router, prefix=V1)
app.include_router(notificaciones.router, prefix=V1)
app.include_router(estadisticas.router, prefix=V1)
app.include_router(match.router, prefix=V1)


@app.get("/", tags=["Sistema"])
async def raiz() -> dict:
    return JSONResponse(
        {
            "servicio": "api-gateway",
            "version": settings.api_version,
            "docs": "/docs",
            "base_url": V1,
        }
    )
