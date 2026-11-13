from fastapi import APIRouter, Depends, Query

from clients import estadisticas_client
from core.envelope import ok
from core.security import Usuario, require_token

router = APIRouter(prefix="/estadisticas", tags=["Estadisticas"])


@router.get("/usuario/{usuario_id}")
async def estadisticas_usuario(
    usuario_id: int,
    periodo: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    materia_id: int | None = Query(default=None, gt=0),
    usuario: Usuario = Depends(require_token),
) -> dict:
    return ok(await estadisticas_client.usuario(usuario_id, periodo=periodo, materia_id=materia_id))


@router.get("/materia/{materia_id}")
async def estadisticas_materia(
    materia_id: int,
    periodo: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    usuario: Usuario = Depends(require_token),
) -> dict:
    return ok(await estadisticas_client.materia(materia_id, periodo=periodo))


@router.get("/grupo/{grupo_id}")
async def estadisticas_grupo(grupo_id: int, usuario: Usuario = Depends(require_token)) -> dict:
    return ok(await estadisticas_client.grupo(grupo_id))
