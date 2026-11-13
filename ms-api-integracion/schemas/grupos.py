from pydantic import BaseModel, Field


class GrupoCrear(BaseModel):
    nombre: str = Field(..., min_length=1)
    materia_id: int = Field(..., gt=0)
    integrantes: list[int] = Field(default_factory=list)
    enlace_zoom: str | None = None
    enlace_jam: str | None = None


class IntegranteAgregar(BaseModel):
    usuario_id: int = Field(..., gt=0)
