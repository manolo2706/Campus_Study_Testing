from datetime import date, time
from typing import Annotated, Literal

from pydantic import BaseModel, Field

Id = Annotated[int, Field(gt=0)]


# ---------- Eventos que recibe (contrato con tareas, grupos y materias) ----------

class TareaPayload(BaseModel):
    tarea_id: Id
    usuario_id: Id
    materia_id: Id
    grupo_id: Id | None = None
    estado: Literal["pendiente", "en_progreso", "completada", "cancelada"]
    fecha_entrega: date
    hora_entrega: time | None = None


class IntegrantePayload(BaseModel):
    usuario_id: Id


class GrupoPayload(BaseModel):
    grupo_id: Id
    nombre: str
    materia_id: Id
    integrantes: list[IntegrantePayload]
class MateriaPayload(BaseModel):
    materia_id: Id
    nombre: str
    nrc: str = Field(min_length=1, max_length=20)

class EventoTarea(BaseModel):
    evento_id: str = Field(min_length=1, max_length=80)
    evento: Literal["tarea.creada", "tarea.actualizada", "tarea.estado_cambiado"]
    payload: TareaPayload


class EventoGrupo(BaseModel):
    evento_id: str = Field(min_length=1, max_length=80)
    evento: Literal["grupo.creado", "grupo.actualizado"]
    payload: GrupoPayload


class EventoMateria(BaseModel):
    evento_id: str = Field(min_length=1, max_length=80)
    evento: Literal["materia.creada", "materia.actualizada"]
    payload: MateriaPayload


# Según "evento", Pydantic sabe qué forma debe tener "payload"
EventoEntrada = Annotated[EventoTarea | EventoGrupo | EventoMateria, Field(discriminator="evento")]


class EventoRespuesta(BaseModel):
    evento_id: str
    duplicado: bool


# ---------- Reportes que entrega (contrato I.10, schema Zod del front) ----------

class TareasResumen(BaseModel):
    total: int
    completadas: int
    pendientes: int
    vencidas: int
    porcentaje_completado: float


class GruposResumen(BaseModel):
    total_grupos: int
    grupos_activos: int


class MateriaResumen(BaseModel):
    materia_id: int
    nombre: str
    tareas_completadas: int
    tareas_total: int


class EstadisticasUsuario(BaseModel):
    usuario_id: int
    nombre: str
    periodo: str | None = None
    tareas: TareasResumen
    grupos: GruposResumen
    materias: list[MateriaResumen]
    fecha_calculo: str


class EstadisticasMateria(BaseModel):
    materia_id: int
    nombre: str
    periodo: str | None = None
    tareas: TareasResumen
    grupos: GruposResumen
    fecha_calculo: str


class EstadisticasGrupo(BaseModel):
    grupo_id: int
    nombre: str
    materia_id: int
    integrantes: int
    tareas: TareasResumen
    fecha_calculo: str