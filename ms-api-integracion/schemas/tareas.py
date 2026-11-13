from pydantic import BaseModel, Field


class TareaCrear(BaseModel):
    usuario_id: int = Field(..., gt=0)
    materia_id: int = Field(..., gt=0)
    titulo: str = Field(..., min_length=1)
    descripcion: str | None = None
    fecha_entrega: str = Field(..., description="YYYY-MM-DD")
    hora_entrega: str = Field(..., description="HH:MM")
    estado: str = Field(default="pendiente")


class TareaActualizar(BaseModel):
    usuario_id: int | None = Field(default=None, gt=0)
    materia_id: int | None = Field(default=None, gt=0)
    titulo: str | None = Field(default=None, min_length=1)
    descripcion: str | None = None
    fecha_entrega: str | None = None
    hora_entrega: str | None = None
    estado: str | None = None
