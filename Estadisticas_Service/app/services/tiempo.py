from datetime import datetime, timedelta, timezone

# Colombia no tiene horario de verano: un offset fijo de -5 es exacto
# y no depende de tzdata (que no viene en Windows)
ZONA_COLOMBIA = timezone(timedelta(hours=-5), name="America/Bogota")

ESTADOS_CERRADOS = {"completada", "cancelada"}


def _reloj() -> datetime:
    # Separado para que los tests puedan congelar el tiempo
    return datetime.now(ZONA_COLOMBIA)


def ahora() -> datetime:
    """Fecha y hora de Colombia sin zona, igual que se guarda en la base."""
    return _reloj().astimezone(ZONA_COLOMBIA).replace(tzinfo=None)


def hoy_iso() -> str:
    return ahora().date().isoformat()


def estado_efectivo(estado: str, fecha_entrega: datetime | None, momento: datetime) -> str:
    """"vencida" no existe en tareas: se deduce si sigue abierta y ya pasó la entrega."""
    if estado in ESTADOS_CERRADOS:
        return estado
    if fecha_entrega and fecha_entrega < momento:
        return "vencida"
    return estado