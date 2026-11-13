from fastapi import APIRouter, Depends, Query

from clients import materias_client
from core.envelope import ok
from core.errors import NotFound
from core.security import Usuario, require_token

router = APIRouter(prefix="/materias", tags=["Materias"])


@router.get("")
async def listar_materias(
    semestre: int | None = Query(default=None),
    termino: str | None = Query(default=None),
    usuario_id: int | None = Query(default=None),
    usuario: Usuario = Depends(require_token),
) -> dict:
    materias = await materias_client.listar(usuario_id=usuario_id, semestre=semestre, termino=termino)
    return ok(materias)


@router.get("/{materia_id}")
async def detalle_materia(materia_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    materia = await materias_client.detalle(materia_id)
    if materia is None:
        raise NotFound("Materia no encontrada", f"materia_id={materia_id} no existe")
    return ok(materia)
