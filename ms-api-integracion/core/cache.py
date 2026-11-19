import time
from typing import Any

from core.config import settings


class TTLCache:
    def __init__(self, ttl: float | None = None) -> None:
        self._ttl = ttl if ttl is not None else settings.cache_ttl_seconds
        self._datos: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._datos.get(key)
        if item is None:
            return None
        expira, valor = item
        if time.monotonic() >= expira:
            self._datos.pop(key, None)
            return None
        return valor

    def set(self, key: str, valor: Any) -> None:
        self._datos[key] = (time.monotonic() + self._ttl, valor)

    def clear(self) -> None:
        self._datos.clear()


cache = TTLCache()
