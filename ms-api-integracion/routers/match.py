from fastapi import APIRouter, Depends, Query

from clients import notificaciones_client
from core.envelope import ok
from core.security import Usuario, headers_to, require_token
from events.publisher import event_publisher
from services import matching

router = APIRouter(prefix="/match", tags=["Matching"])


@router.get("/companeros")
async def companeros(
    materia_id: int = Query(..., gt=0),
    habilidad: str | None = Query(default=None),
    usuario: Usuario = Depends(require_token),
) -> dict:
    headers = headers_to(usuario, "grupos")
    return ok(await matching.sugerir_companeros(usuario, materia_id=materia_id, habilidad=habilidad, headers=headers))


@router.get("/sugerencias/{usuario_id}")
async def sugerencias(usuario_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "grupos")
    return ok(await matching.sugerencias_generales(usuario, headers=headers))


@router.post("/{usuario_id}/solicitud", status_code=202)
async def solicitud(usuario_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "grupos")
    resultado = await matching.enviar_solicitud(usuario, usuario_id, headers=headers)

    notificacion = {}
    try:
        notificacion = await notificaciones_client.crear(
            usuario_id,
            tipo="solicitud_match",
            titulo="Nueva solicitud de companero",
            mensaje=f"El usuario {resultado['de']} quiere ser tu companero de estudio",
            referencia_id=resultado["de"],
        )
    except Exception:
        notificacion = {}

    event_publisher.publicar("match.solicitud_enviada", resultado)

    respuesta = {
        "solicitud_id": resultado["de"],
        "de": resultado["de"],
        "para": resultado["para"],
        "estado": resultado["estado"],
        "notificacion_id": (notificacion or {}).get("notificacion_id"),
    }
    return ok(respuesta)
