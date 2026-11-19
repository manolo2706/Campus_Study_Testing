from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EstadisticasGrupo, EstadisticasMateria, EstadisticasUsuario
from app.security import UsuarioActual
from app.services.agregador import (
    estadisticas_grupo,
    estadisticas_materia,
    estadisticas_usuario,
)

router = APIRouter(prefix="/api/v1/estadisticas", tags=["estadisticas"])

Db = Annotated[Session, Depends(get_db)]
Periodo = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")]


def _no_encontrado(recurso: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"codigo": 404, "mensaje": f"{recurso} no encontrado"})


@router.get("/me", response_model=EstadisticasUsuario, response_model_exclude_none=True)
def mi_reporte(
    usuario: UsuarioActual,
    db: Db,
    periodo: Periodo = None,
    materia_id: Annotated[int | None, Query(gt=0)] = None,
) -> EstadisticasUsuario:
    return estadisticas_usuario(db, usuario.usuario_id, usuario.nombre, periodo, materia_id)


@router.get("/materia/{materia_id}", response_model=EstadisticasMateria, response_model_exclude_none=True)
def reporte_materia(
    materia_id: Annotated[int, Path(gt=0)],
    usuario: UsuarioActual,
    db: Db,
    periodo: Periodo = None,
) -> EstadisticasMateria:
    reporte = estadisticas_materia(db, materia_id, usuario.usuario_id, periodo)
    if not reporte:
        raise _no_encontrado("Materia")
    return reporte


@router.get("/grupo/{grupo_id}", response_model=EstadisticasGrupo)
def reporte_grupo(
    grupo_id: Annotated[int, Path(gt=0)],
    usuario: UsuarioActual,
    db: Db,
) -> EstadisticasGrupo:
    reporte = estadisticas_grupo(db, grupo_id, usuario.usuario_id)
    if not reporte:
        raise _no_encontrado("Grupo")
    return reporte