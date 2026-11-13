"""Microservicio de Tareas — CampusStudy.

Implementa el Contrato de Interfaz e Integración versión 1.0 del Grupo #1.
Documentación interactiva: http://localhost:8001/docs
"""
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app import contexto, notificaciones
from app.clientes import estado_dependencias
from app.config import config
from app.database import Base, motor
from app.errores import ErrorContrato
from app.respuestas import error, exito
from app.routers import tareas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("ms-tareas")


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    Base.metadata.create_all(bind=motor)
    tarea = asyncio.create_task(notificaciones.tarea_periodica())
    log.info(
        "Servicio de Tareas iniciado (contrato v%s) | modo=%s",
        config.version_contrato,
        "simulado" if config.simular_servicios else "integración",
    )
    if not config.simular_servicios:
        log.info(
            "Servicios configurados -> usuarios=%s materias=%s grupos=%s notificaciones=%s",
            config.url_usuarios, config.url_materias,
            config.url_grupos, config.url_notificaciones,
        )
    yield
    tarea.cancel()


app = FastAPI(
    title="CampusStudy — Servicio de Tareas",
    description="Contrato de Interfaz e Integración v1.0 · Grupo #1",
    version=config.version_contrato,
    lifespan=ciclo_vida,
)

# El Front (#6) se ejecuta en otro origen, así que el navegador exige CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.origenes,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)

app.include_router(tareas.router)


@app.middleware("http")
async def trazabilidad(request: Request, call_next):
    """Propaga el header X-Request-Id acordado en el contrato.

    Si la petición ya trae uno (porque viene del API Gateway) se conserva, de modo
    que un mismo identificador permita seguir la operación por todos los servicios.
    """
    identificador = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    contexto.fijar_request_id(identificador)
    contexto.fijar_token("")
    request.state.request_id = identificador
    respuesta = await call_next(request)
    respuesta.headers["X-Request-Id"] = identificador
    return respuesta


@app.exception_handler(ErrorContrato)
async def manejar_error_contrato(request: Request, exc: ErrorContrato):
    if exc.codigo >= 500:
        log.error("%s | %s | request_id=%s", exc.tipo, exc.mensaje,
                  getattr(request.state, "request_id", "-"))
    return error(exc.codigo, exc.tipo, exc.mensaje)


@app.exception_handler(RequestValidationError)
async def manejar_validacion(request: Request, exc: RequestValidationError):
    """El contrato exige 400 para datos inválidos, no el 422 por defecto."""
    detalles = []
    for e in exc.errors():
        campo = ".".join(str(p) for p in e["loc"] if p not in ("body", "query"))
        detalles.append(f"{campo}: {e['msg']}" if campo else e["msg"])
    return error(400, "SOLICITUD_INCORRECTA", "; ".join(detalles))


@app.exception_handler(Exception)
async def manejar_error_inesperado(request: Request, exc: Exception):
    log.exception("Error inesperado | request_id=%s", getattr(request.state, "request_id", "-"))
    return error(500, "ERROR_INTERNO", "Ocurrió un error interno en el servicio de Tareas")


@app.get("/salud", tags=["Servicio"])
def salud():
    """Permite a los demás equipos verificar que el servicio está arriba."""
    return exito(
        {
            "servicio": config.nombre_servicio,
            "version_contrato": config.version_contrato,
            "api": f"/api/{config.version_api}/",
            "modo": "simulado" if config.simular_servicios else "integración",
        },
        "Servicio disponible",
    )


@app.get("/salud/dependencias", tags=["Servicio"])
async def salud_dependencias():
    """Muestra qué servicios externos están respondiendo en este momento.

    Sirve para la reunión de integración: de un vistazo se ve quién está arriba
    y quién no, sin tener que revisar los logs.
    """
    estados = await estado_dependencias()
    hay_caidos = any(v == "sin respuesta" for v in estados.values())
    return exito(
        {
            "servicio": config.nombre_servicio,
            "dependencias": estados,
            "urls": {
                "usuarios": config.url_usuarios,
                "materias": config.url_materias,
                "grupos": config.url_grupos,
                "notificaciones": config.url_notificaciones,
            },
        },
        "Hay servicios sin respuesta" if hay_caidos else "Todas las dependencias responden",
    )
