from fastapi import APIRouter, Depends, Query

from clients import notificaciones_client
from core.envelope import ok
from core.security import Usuario, require_token
from schemas.notificaciones import NotificacionCrear

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


@router.get("")
async def listar_notificaciones(
    usuario_id: int = Query(...),
    solo_no_leidas: bool = Query(default=False),
    usuario: Usuario = Depends(require_token),
) -> dict:
    return ok(await notificaciones_client.listar(usuario_id, solo_no_leidas=solo_no_leidas))


@router.post("", status_code=201)
async def publicar_notificacion(body: NotificacionCrear, usuario: Usuario = Depends(require_token)) -> dict:
    return ok(
        await notificaciones_client.crear(
            body.usuario_id,
            tipo=body.tipo,
            titulo=body.titulo,
            mensaje=body.mensaje,
            estado=body.estado,
            referencia_id=body.referencia_id,
        )
    )


@router.patch("/{notificacion_id}")
async def marcar_leida(notificacion_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    return ok(await notificaciones_client.marcar_leida(notificacion_id))


@router.post("/marcar-todas")
async def marcar_todas(usuario_id: int = Query(...), usuario: Usuario = Depends(require_token)) -> dict:
    return ok(await notificaciones_client.marcar_todas(usuario_id))
