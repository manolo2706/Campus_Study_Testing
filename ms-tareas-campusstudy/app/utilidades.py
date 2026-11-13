"""Formatos de fecha y hora acordados en el contrato (sección I)."""
from datetime import date, datetime, timedelta, timezone

FORMATO_FECHA = "%Y-%m-%d"
FORMATO_HORA = "%H:%M"
FORMATO_FECHA_HORA = "%Y-%m-%dT%H:%M:%S"

# Hora de Colombia (UTC-5), sin depender de la configuración del sistema operativo.
UTC_MENOS_5 = timezone(timedelta(hours=-5))


def ahora() -> datetime:
    return datetime.now(UTC_MENOS_5).replace(tzinfo=None)


def hoy() -> date:
    return ahora().date()


def fecha_texto(valor) -> str | None:
    return valor.strftime(FORMATO_FECHA) if valor else None


def fecha_hora_texto(valor) -> str | None:
    return valor.strftime(FORMATO_FECHA_HORA) if valor else None
