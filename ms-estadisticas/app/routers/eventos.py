from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EventoEntrada, EventoRespuesta
from app.services.eventos import procesar_evento

router = APIRouter(prefix="/api/v1/eventos", tags=["eventos"])

Db = Annotated[Session, Depends(get_db)]


@router.post("", response_model=EventoRespuesta)
def recibir_evento(entrada: EventoEntrada, db: Db) -> EventoRespuesta:
    """Interno: lo llaman tareas, grupos y materias por la red de Docker. El gateway no lo expone."""
    return procesar_evento(db, entrada)