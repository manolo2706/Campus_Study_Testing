import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from clients.estadisticas_client import estadisticas_client

logger = logging.getLogger("campusstudy.events")


@dataclass
class Evento:
    nombre: str
    payload: dict = field(default_factory=dict)
    version: str = "1.0"
    evento_id: str = field(default_factory=lambda: str(uuid4()))
    intentos: int = 0


class EventPublisher:
    def __init__(self, max_intentos: int = 3) -> None:
        self._cola: asyncio.Queue[Evento] = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._max_intentos = max_intentos

    async def iniciar(self) -> None:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._procesar())

    async def detener(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None

    def publicar(self, nombre: str, payload: dict, *, version: str = "1.0") -> None:
        self._cola.put_nowait(Evento(nombre=nombre, payload=payload, version=version))

    async def _procesar(self) -> None:
        while True:
            evento = await self._cola.get()
            try:
                await self._entregar(evento)
            finally:
                self._cola.task_done()

    async def _entregar(self, evento: Evento) -> None:
        while evento.intentos <= self._max_intentos:
            try:
                await estadisticas_client.publicar_evento(
                    evento.nombre,
                    evento.payload,
                    version=evento.version,
                    evento_id=evento.evento_id,
                )
                logger.info("evento publicado: %s (%s)", evento.nombre, evento.evento_id)
                return
            except Exception as exc:
                evento.intentos += 1
                if evento.intentos > self._max_intentos:
                    logger.warning("evento descartado tras %s intentos: %s (%s)", evento.intentos, evento.nombre, exc)
                    return
                await asyncio.sleep(min(0.5 * (2**evento.intentos), 5.0))


event_publisher = EventPublisher()


def ahora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
