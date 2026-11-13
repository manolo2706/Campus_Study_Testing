from fastapi import APIRouter, Depends, Query, Response

from clients import tareas_client
from core.envelope import ok
from core.security import Usuario, headers_to, require_token
from events.publisher import event_publisher
from schemas.tareas import TareaCrear, TareaActualizar

router = APIRouter(prefix="/tareas", tags=["Tareas"])


@router.get("")
async def listar_tareas(
    usuario_id: int | None = Query(default=None),
    materia_id: int | None = Query(default=None),
    grupo_id: int | None = Query(default=None),
    estado: str | None = Query(default=None),
    fecha_limite: str | None = Query(default=None),
    usuario: Usuario = Depends(require_token),
) -> dict:
    headers = headers_to(usuario, "tareas")
    tareas = await tareas_client.listar(
        usuario_id=usuario_id,
        materia_id=materia_id,
        grupo_id=grupo_id,
        estado=estado,
        fecha_limite=fecha_limite,
        headers=headers,
    )
    return ok(tareas)


@router.post("", status_code=201)
async def crear_tarea(body: TareaCrear, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "tareas")
    tarea = await tareas_client.crear(body.model_dump(), headers=headers)
    event_publisher.publicar("tarea.creada", tarea)
    return ok(tarea)


@router.get("/{tarea_id}")
async def detalle_tarea(tarea_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "tareas")
    return ok(await tareas_client.detalle(tarea_id, headers=headers))


@router.put("/{tarea_id}")
async def actualizar_tarea(tarea_id: int, body: TareaActualizar, usuario: Usuario = Depends(require_token)) -> dict:
    headers = headers_to(usuario, "tareas")
    anterior = await tareas_client.detalle(tarea_id, headers=headers)
    tarea = await tareas_client.actualizar(tarea_id, body.model_dump(exclude_unset=True), headers=headers)
    if body.estado is not None and anterior and anterior.get("estado") != body.estado:
        event_publisher.publicar("tarea.estado_cambiado", tarea)
    else:
        event_publisher.publicar("tarea.actualizada", tarea)
    return ok(tarea)


@router.delete("/{tarea_id}", status_code=204)
async def eliminar_tarea(tarea_id: int, usuario: Usuario = Depends(require_token)) -> Response:
    headers = headers_to(usuario, "tareas")
    await tareas_client.eliminar(tarea_id, headers=headers)
    event_publisher.publicar("tarea.eliminada", {"tarea_id": tarea_id})
    return Response(status_code=204)
