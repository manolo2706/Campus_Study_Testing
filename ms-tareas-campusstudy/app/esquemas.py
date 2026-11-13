"""Validación de entrada y salida según las reglas de datos del contrato (sección I)."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utilidades import FORMATO_FECHA, FORMATO_HORA, fecha_hora_texto, fecha_texto, hoy

ESTADOS = ("pendiente", "en_progreso", "completada", "cancelada")
PRIORIDADES = ("baja", "media", "alta")

# Transiciones permitidas. Una tarea completada o cancelada no vuelve a pendiente.
TRANSICIONES = {
    "pendiente": {"en_progreso", "completada", "cancelada"},
    "en_progreso": {"completada", "cancelada"},
    "completada": set(),
    "cancelada": set(),
}


def _validar_fecha(valor: str) -> date:
    try:
        return datetime.strptime(valor, FORMATO_FECHA).date()
    except (TypeError, ValueError):
        raise ValueError("fecha_entrega debe tener el formato YYYY-MM-DD")


def _validar_hora(valor: Optional[str]) -> Optional[str]:
    if valor in (None, ""):
        return None
    try:
        datetime.strptime(valor, FORMATO_HORA)
    except ValueError:
        raise ValueError("hora_entrega debe tener el formato HH:MM en 24 horas")
    return valor


class TareaCrear(BaseModel):
    titulo: str = Field(min_length=1, max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    usuario_id: int = Field(gt=0)
    materia_id: int = Field(gt=0)
    grupo_id: Optional[int] = Field(default=None, gt=0)
    fecha_entrega: str
    hora_entrega: Optional[str] = None
    prioridad: Literal[PRIORIDADES] = "media"  # type: ignore[valid-type]

    @field_validator("fecha_entrega")
    @classmethod
    def revisar_fecha(cls, v):
        fecha = _validar_fecha(v)
        if fecha < hoy():
            raise ValueError("fecha_entrega no puede ser anterior a la fecha de creación")
        return v

    @field_validator("hora_entrega")
    @classmethod
    def revisar_hora(cls, v):
        return _validar_hora(v)


class TareaActualizar(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    fecha_entrega: Optional[str] = None
    hora_entrega: Optional[str] = None
    prioridad: Optional[Literal[PRIORIDADES]] = None  # type: ignore[valid-type]

    @field_validator("fecha_entrega")
    @classmethod
    def revisar_fecha(cls, v):
        if v is None:
            return v
        _validar_fecha(v)
        return v

    @field_validator("hora_entrega")
    @classmethod
    def revisar_hora(cls, v):
        return _validar_hora(v)

    @model_validator(mode="after")
    def al_menos_un_campo(self):
        if not any(
            getattr(self, c) is not None
            for c in ("titulo", "descripcion", "fecha_entrega", "hora_entrega", "prioridad")
        ):
            raise ValueError("debe enviar al menos un campo para actualizar")
        return self


class CambioEstado(BaseModel):
    estado: Literal[ESTADOS]  # type: ignore[valid-type]


def tarea_completa(t) -> dict:
    """Estructura de respuesta de una tarea, tal como la define el contrato."""
    return {
        "tarea_id": t.tarea_id,
        "titulo": t.titulo,
        "descripcion": t.descripcion,
        "usuario_id": t.usuario_id,
        "materia_id": t.materia_id,
        "grupo_id": t.grupo_id,
        "fecha_entrega": fecha_texto(t.fecha_entrega),
        "hora_entrega": t.hora_entrega,
        "prioridad": t.prioridad,
        "estado": t.estado,
        "fecha_creacion": fecha_hora_texto(t.fecha_creacion),
        "fecha_actualizacion": fecha_hora_texto(t.fecha_actualizacion),
    }


def tarea_resumida(t) -> dict:
    """Estructura usada en los listados."""
    return {
        "tarea_id": t.tarea_id,
        "titulo": t.titulo,
        "materia_id": t.materia_id,
        "fecha_entrega": fecha_texto(t.fecha_entrega),
        "estado": t.estado,
    }
