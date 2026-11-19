import asyncio

import httpx
from fastapi import APIRouter

from core.config import settings
from core.envelope import ok

router = APIRouter(tags=["Sistema"])

SONDEOS = {
    "user_autenticacion": (settings.auth_url, "/api/v1/auth/login"),
    "materias": (settings.materias_url, "/health"),
    "tareas": (settings.tareas_url, "/health"),
    "grupos": (settings.grupos_url, "/api/v1/grupos"),
    "notificaciones": (settings.notificaciones_url, "/"),
    "estadisticas": (settings.estadisticas_url, "/salud"),
}


async def _probar(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
            response = await client.get(url)
        if response.status_code < 500:
            return "ok"
        return "caido"
    except Exception:
        return "caido"


async def _estado_servicios() -> dict:
    if settings.stubs_enabled:
        return {"api": "ok", **{nombre: "ok" for nombre in SONDEOS}}
    tareas = [_probar(f"{base}{path}") for base, path in SONDEOS.values()]
    resultados = await asyncio.gather(*tareas)
    data = {"api": "ok"}
    for nombre, estado in zip(SONDEOS.keys(), resultados):
        data[nombre] = estado
    return data


@router.get("/health")
async def health() -> dict:
    return ok(await _estado_servicios())
