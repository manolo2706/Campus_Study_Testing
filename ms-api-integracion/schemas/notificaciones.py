from pydantic import BaseModel, Field


class NotificacionCrear(BaseModel):
    usuario_id: int = Field(..., gt=0)
    tipo: str = Field(..., min_length=1)
    titulo: str = Field(..., min_length=1)
    mensaje: str = Field(..., min_length=1)
    estado: str = Field(default="pendiente")
    referencia_id: int | None = None
