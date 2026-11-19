from fastapi import APIRouter, Depends, Query, Response

from clients import grupos_client, notificaciones_client
from core.envelope import ok
from core.security import Usuario, headers_to, require_token
from events.publisher import event_publisher
from schemas.grupos import GrupoCrear, IntegranteAgregar

router = APIRouter(prefix="/grupos", tags=["Grupos"])


@router.get("")
async def listar_grupos(
    materia_id: int | None = Query(default=None),
    usuario: Usuario = Depends(require_token),
) -> dict:
    headers = headers_to(usuario, "grupos")
    return ok(await grupos_client.listar(materia_id=materia_id, headers=headers))


@router.post("", status_code=201)
async def crear_grupo(body: GrupoCrear, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "grupos")
    payload = body.model_dump(exclude_none=True)
    payload["creado_por"] = usuario.usuario_id
    grupo = await grupos_client.crear(payload, headers=headers)
    event_publisher.publicar("grupo.creado", grupo)
    return ok(grupo)


@router.get("/{grupo_id}")
async def detalle_grupo(grupo_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "grupos")
    return ok(await grupos_client.detalle(grupo_id, headers=headers))


@router.post("/{grupo_id}/integrantes", status_code=201)
async def agregar_integrante(
    grupo_id: int,
    body: IntegranteAgregar,
    usuario: Usuario = Depends(require_token),
) -> dict:
    headers = headers_to(usuario, "grupos")
    resultado = await grupos_client.agregar_integrante(grupo_id, body.usuario_id, headers=headers)
    payload = {"grupo_id": grupo_id, "usuario_id": body.usuario_id, "rol": "miembro"}
    event_publisher.publicar("grupo.miembro_agregado", payload)
    try:
        await notificaciones_client.crear(
            body.usuario_id,
            tipo="grupo",
            titulo="Te agregaron a un grupo",
            mensaje=f"Fuiste agregado al grupo {grupo_id}",
            referencia_id=grupo_id,
        )
    except Exception:
        pass
    return ok(resultado)


@router.delete("/{grupo_id}/integrantes/{usuario_id}", status_code=204)
async def retirar_integrante(
    grupo_id: int,
    usuario_id: int,
    usuario: Usuario = Depends(require_token),
) -> Response:
    headers = headers_to(usuario, "grupos")
    await grupos_client.retirar_integrante(grupo_id, usuario_id, headers=headers)
    event_publisher.publicar(
        "grupo.miembro_retirado", {"grupo_id": grupo_id, "usuario_id": usuario_id}
    )
    return Response(status_code=204)
