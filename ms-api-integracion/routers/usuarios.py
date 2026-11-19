import asyncio

from fastapi import APIRouter, Depends

from clients import auth_client, grupos_client, materias_client, tareas_client
from core.envelope import ok
from core.errors import ApiError, NotFound
from core.security import Usuario, headers_to, require_token

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


async def _con_degradacion(coro, servicio: str, default):
    try:
        return await coro, None
    except ApiError as exc:
        return default, {"servicio": servicio, "motivo": exc.message, "codigo": exc.status_code}
    except Exception as exc:  # noqa: BLE001
        return default, {"servicio": servicio, "motivo": str(exc), "codigo": 500}


@router.get("/{usuario_id}")
async def perfil(usuario_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    perfil = await auth_client.get_usuario(usuario_id)
    if perfil is None:
        raise NotFound("Usuario no encontrado", f"usuario_id={usuario_id} no existe")
    return ok(perfil)


@router.get("/{usuario_id}/materias")
async def materias_de_usuario(usuario_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "materias")
    materias, warning = await _con_degradacion(
        materias_client.materias_estudiante(usuario_id), "materias", []
    )
    if materias == [] and warning and warning.get("codigo") == 503:
        raise ApiError(503, "Servicio temporalmente no disponible", warning["motivo"])
    return ok(materias, warnings=[warning] if warning else None)


@router.get("/{usuario_id}/tareas")
async def tareas_de_usuario(usuario_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "tareas")
    tareas, warning = await _con_degradacion(
        tareas_client.listar(usuario_id=usuario_id, headers=headers), "tareas", []
    )
    if tareas == [] and warning and warning.get("codigo") == 503:
        raise ApiError(503, "Servicio temporalmente no disponible", warning["motivo"])
    return ok(tareas, warnings=[warning] if warning else None)


@router.get("/{usuario_id}/grupos")
async def grupos_de_usuario(usuario_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "grupos")
    grupos, warning = await _con_degradacion(
        grupos_client.grupos_de_usuario(usuario_id, headers=headers), "grupos", []
    )
    if grupos == [] and warning and warning.get("codigo") == 503:
        raise ApiError(503, "Servicio temporalmente no disponible", warning["motivo"])
    return ok(grupos, warnings=[warning] if warning else None)


@router.get("/{usuario_id}/resumen")
async def resumen_usuario(usuario_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    headers_materias = headers_to(usuario, "materias")
    headers_tareas = headers_to(usuario, "tareas")
    headers_grupos = headers_to(usuario, "grupos")

    perfil_r = _con_degradacion(auth_client.get_usuario(usuario_id), "auth", None)
    materias_r = _con_degradacion(materias_client.materias_estudiante(usuario_id), "materias", [])
    tareas_r = _con_degradacion(tareas_client.listar(usuario_id=usuario_id, headers=headers_tareas), "tareas", [])
    grupos_r = _con_degradacion(grupos_client.grupos_de_usuario(usuario_id, headers=headers_grupos), "grupos", [])

    (perfil, w1), (materias, w2), (tareas, w3), (grupos, w4) = await asyncio.gather(
        perfil_r, materias_r, tareas_r, grupos_r
    )
    warnings = [w for w in (w1, w2, w3, w4) if w]
    data = {
        "usuario": perfil,
        "materias": materias,
        "tareas": tareas,
        "grupos": grupos,
    }
    return ok(data, warnings=warnings or None)
