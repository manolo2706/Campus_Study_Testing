from datetime import datetime, time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    EventoRecibido,
    GrupoProyeccion,
    MateriaProyeccion,
    MiembroGrupo,
    TareaProyeccion,
)
from app.schemas import (
    EventoEntrada,
    EventoRespuesta,
    GrupoPayload,
    MateriaPayload,
    TareaPayload,
)

# Sin hora de entrega, la tarea vence al final del día (contrato I.6)
FIN_DEL_DIA = time(23, 59)


def procesar_evento(db: Session, entrada: EventoEntrada) -> EventoRespuesta:
    # Idempotencia: el mismo evento dos veces (reintento de Polly, RabbitMQ) no cuenta doble
    if db.query(EventoRecibido.id).filter_by(evento_id=entrada.evento_id).first():
        return EventoRespuesta(evento_id=entrada.evento_id, duplicado=True)

    match entrada.payload:
        case TareaPayload() as tarea:
            _guardar_tarea(db, tarea)
        case GrupoPayload() as grupo:
            _guardar_grupo(db, grupo)
        case MateriaPayload() as materia:
            _guardar_materia(db, materia)

    db.add(EventoRecibido(
        evento_id=entrada.evento_id,
        tipo=entrada.evento,
        payload_json=entrada.payload.model_dump_json(),
    ))

    try:
        db.commit()
    except IntegrityError:
        # Dos copias del mismo evento llegaron al mismo tiempo: la otra ya lo aplicó
        db.rollback()
        return EventoRespuesta(evento_id=entrada.evento_id, duplicado=True)

    return EventoRespuesta(evento_id=entrada.evento_id, duplicado=False)


# Cada evento trae la foto completa de la entidad: se guarda tal cual (upsert)

def _guardar_tarea(db: Session, tarea: TareaPayload) -> None:
    db.merge(TareaProyeccion(
        id=tarea.tarea_id,
        usuario_id=tarea.usuario_id,
        materia_id=tarea.materia_id,
        grupo_id=tarea.grupo_id,
        estado=tarea.estado,
        fecha_entrega=datetime.combine(tarea.fecha_entrega, tarea.hora_entrega or FIN_DEL_DIA),
    ))


def _guardar_grupo(db: Session, grupo: GrupoPayload) -> None:
    db.merge(GrupoProyeccion(id=grupo.grupo_id, nombre=grupo.nombre, materia_id=grupo.materia_id))

    # grupos-service manda la lista completa: se reemplaza la anterior
    db.query(MiembroGrupo).filter_by(grupo_id=grupo.grupo_id).delete()
    db.add_all(MiembroGrupo(grupo_id=grupo.grupo_id, usuario_id=i.usuario_id) for i in grupo.integrantes)

def _guardar_materia(db: Session, materia: MateriaPayload) -> None:
    db.merge(MateriaProyeccion(id=materia.materia_id, nombre=materia.nombre, nrc=materia.nrc))