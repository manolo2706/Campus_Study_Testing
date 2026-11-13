"""Envío de eventos al servicio de Notificaciones.

Regla del contrato: si Notificaciones no responde, la tarea igual se registra y el
evento queda pendiente, con reintentos cada 5 minutos hasta por 24 horas.
"""
import asyncio
import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.clientes import INTEGRANTES_SIMULADOS, consultar_grupo, enviar_notificacion
from app.config import config
from app.database import Sesion
from app.errores import ErrorContrato
from app.models import EventoPendiente
from app.utilidades import ahora, fecha_hora_texto

log = logging.getLogger("ms-tareas.notificaciones")

MENSAJES = {
    "tarea_creada": "Nueva tarea: {titulo}. Entrega: {entrega}",
    "tarea_actualizada": "La tarea {titulo} fue modificada. Entrega: {entrega}",
    "tarea_cancelada": "La tarea {titulo} fue cancelada",
    "tarea_proxima_vencer": "La tarea {titulo} vence el {entrega}",
}


async def destinatarios(tarea) -> list[int]:
    """Si la tarea es de grupo se notifica a cada integrante."""
    if not tarea.grupo_id:
        return [tarea.usuario_id]
    try:
        grupo = await consultar_grupo(tarea.grupo_id)
        if grupo and grupo.get("integrantes"):
            return list(grupo["integrantes"])
    except ErrorContrato:
        log.warning("No se pudo consultar el grupo %s para notificar", tarea.grupo_id)
    return [tarea.usuario_id]


async def notificar(bd: Session, tarea, tipo: str) -> None:
    entrega = f"{tarea.fecha_entrega} {tarea.hora_entrega or ''}".strip()
    mensaje = MENSAJES[tipo].format(titulo=tarea.titulo, entrega=entrega)
    momento = ahora()

    for usuario_id in await destinatarios(tarea):
        evento = {
            "usuario_id": usuario_id,
            "tipo": tipo,
            "referencia_id": tarea.tarea_id,
            "mensaje": mensaje,
            "fecha_evento": fecha_hora_texto(momento),
        }
        try:
            await enviar_notificacion(evento)
        except ErrorContrato:
            # No se pierde el evento: queda guardado para reintentar.
            bd.add(
                EventoPendiente(
                    usuario_id=usuario_id,
                    tipo=tipo,
                    referencia_id=tarea.tarea_id,
                    mensaje=mensaje,
                    fecha_evento=momento,
                    intentos=1,
                    ultimo_intento=momento,
                )
            )
            bd.commit()
            log.warning("Evento %s de la tarea %s quedó pendiente", tipo, tarea.tarea_id)


async def reintentar_pendientes() -> int:
    """Reintenta los eventos pendientes y descarta los que ya superaron 24 horas."""
    bd = Sesion()
    enviados = 0
    try:
        limite = ahora() - timedelta(hours=config.horas_maximo_evento)
        for evento in bd.query(EventoPendiente).all():
            if evento.fecha_evento < limite:
                bd.delete(evento)
                log.warning("Evento %s descartado tras %s horas", evento.evento_id,
                            config.horas_maximo_evento)
                continue
            try:
                await enviar_notificacion(
                    {
                        "usuario_id": evento.usuario_id,
                        "tipo": evento.tipo,
                        "referencia_id": evento.referencia_id,
                        "mensaje": evento.mensaje,
                        "fecha_evento": fecha_hora_texto(evento.fecha_evento),
                    }
                )
                bd.delete(evento)
                enviados += 1
            except ErrorContrato:
                evento.intentos += 1
                evento.ultimo_intento = ahora()
        bd.commit()
    finally:
        bd.close()
    return enviados


async def tarea_periodica():
    """Ciclo en segundo plano que reintenta los eventos pendientes."""
    while True:
        await asyncio.sleep(config.minutos_reintento_eventos * 60)
        try:
            await reintentar_pendientes()
        except Exception:  # el ciclo nunca debe detenerse
            log.exception("Error al reintentar los eventos pendientes")
