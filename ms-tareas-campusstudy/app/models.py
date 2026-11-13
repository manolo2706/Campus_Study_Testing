"""Tablas del servicio. Solo almacena identificadores de otros servicios."""
from sqlalchemy import Column, Date, DateTime, Integer, String, Text

from app.database import Base
from app.utilidades import ahora


class Tarea(Base):
    __tablename__ = "tareas"

    tarea_id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    materia_id = Column(Integer, nullable=False, index=True)
    grupo_id = Column(Integer, nullable=True, index=True)
    fecha_entrega = Column(Date, nullable=False, index=True)
    hora_entrega = Column(String(5), nullable=True)
    prioridad = Column(String(10), nullable=False, default="media")
    estado = Column(String(15), nullable=False, default="pendiente", index=True)
    fecha_creacion = Column(DateTime, nullable=False, default=ahora)
    fecha_actualizacion = Column(DateTime, nullable=False, default=ahora, onupdate=ahora)


class EventoPendiente(Base):
    """Eventos que no se pudieron entregar a Notificaciones (sección J del contrato)."""

    __tablename__ = "eventos_pendientes"

    evento_id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=False)
    tipo = Column(String(30), nullable=False)
    referencia_id = Column(Integer, nullable=False)
    mensaje = Column(String(300), nullable=False)
    fecha_evento = Column(DateTime, nullable=False)
    intentos = Column(Integer, nullable=False, default=1)
    ultimo_intento = Column(DateTime, nullable=False, default=ahora)


class PeticionIdempotente(Base):
    """Evita crear dos veces la misma tarea.

    Si la respuesta no le llega al Front porque se cayó la conexión, el estudiante
    puede reintentar. Si la petición trae la misma clave de idempotencia, en lugar
    de crear una tarea nueva se devuelve la que ya se creó.
    """

    __tablename__ = "peticiones_idempotentes"

    clave = Column(String(80), primary_key=True)
    tarea_id = Column(Integer, nullable=False)
    fecha_creacion = Column(DateTime, nullable=False, default=ahora)
