import time
from dataclasses import dataclass, field

from core.config import settings


@dataclass
class _Estado:
    fallos: int = 0
    abierto_hasta: float = 0.0


class CircuitBreaker:
    def __init__(self) -> None:
        self._servicios: dict[str, _Estado] = {}

    def _estado(self, servicio: str) -> _Estado:
        return self._servicios.setdefault(servicio, _Estado())

    def permitir(self, servicio: str) -> bool:
        estado = self._estado(servicio)
        if estado.abierto_hasta and time.monotonic() < estado.abierto_hasta:
            return False
        if estado.abierto_hasta and time.monotonic() >= estado.abierto_hasta:
            estado.fallos = 0
            estado.abierto_hasta = 0.0
        return True

    def registrar_exito(self, servicio: str) -> None:
        estado = self._estado(servicio)
        estado.fallos = 0
        estado.abierto_hasta = 0.0

    def registrar_fallo(self, servicio: str) -> None:
        estado = self._estado(servicio)
        estado.fallos += 1
        if estado.fallos >= settings.circuit_fail_threshold:
            estado.abierto_hasta = time.monotonic() + settings.circuit_recovery_seconds

    def estado_publico(self, servicio: str) -> str:
        estado = self._estado(servicio)
        if estado.abierto_hasta and time.monotonic() < estado.abierto_hasta:
            return "abierto"
        return "cerrado"


circuit_breaker = CircuitBreaker()
