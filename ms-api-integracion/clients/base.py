import asyncio
from typing import Any

import httpx

from core.circuit_breaker import circuit_breaker
from core.config import settings
from core.errors import ApiError, ServiceUnavailable

IDEMPOTENTES = {"GET", "HEAD", "OPTIONS"}


def _extraer_mensaje(payload: Any, status: int) -> str:
    if isinstance(payload, dict):
        for key in ("mensaje", "message", "detail", "error"):
            valor = payload.get(key)
            if isinstance(valor, str) and valor:
                return valor
            if isinstance(valor, dict) and isinstance(valor.get("mensaje"), str):
                return valor["mensaje"]
    return f"el servicio respondio con estado {status}"


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict):
        if "error" in payload and "data" in payload:
            if payload.get("error"):
                err = payload["error"]
                raise ApiError(err.get("codigo", 502), err.get("mensaje", "error del proveedor"), err.get("detalle"))
            return payload.get("data")
        if "exito" in payload and "datos" in payload:
            if payload.get("exito") is False:
                raise ApiError(502, _extraer_mensaje(payload, 502))
            return payload.get("datos")
    return payload


class ServiceClient:
    def __init__(self, nombre: str, base_url: str) -> None:
        self.nombre = nombre
        self.base_url = base_url.rstrip("/")

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
        headers: dict | None = None,
        permitir_reintento: bool | None = None,
        cache_key: str | None = None,
    ) -> Any:
        from core.cache import cache

        if cache_key is not None:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        if not circuit_breaker.permitir(self.nombre):
            raise ServiceUnavailable(
                self.nombre,
                f"circuito abierto para '{self.nombre}' (recuperacion en curso)",
            )

        if permitir_reintento is None:
            permitir_reintento = method.upper() in IDEMPOTENTES

        timeout = httpx.Timeout(settings.request_timeout, connect=settings.connect_timeout)
        url = f"{self.base_url}{path}"
        intentos = settings.max_retries + 1 if permitir_reintento else 1
        ultimo_error: Exception | None = None

        for intento in range(intentos):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, params=params, json=json, headers=headers)
                if response.status_code >= 500:
                    circuit_breaker.registrar_fallo(self.nombre)
                    payload = self._safe_json(response)
                    raise ApiError(response.status_code, _extraer_mensaje(payload, response.status_code))
                if response.status_code >= 400:
                    payload = self._safe_json(response)
                    raise ApiError(response.status_code, _extraer_mensaje(payload, response.status_code))
                circuit_breaker.registrar_exito(self.nombre)
                resultado = _unwrap(self._safe_json(response))
                if cache_key is not None:
                    cache.set(cache_key, resultado)
                return resultado
            except ApiError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                ultimo_error = exc
                if intento < intentos - 1:
                    delay = min(settings.retry_base_delay * (2**intento), settings.retry_max_delay)
                    await asyncio.sleep(delay)

        circuit_breaker.registrar_fallo(self.nombre)
        raise ServiceUnavailable(self.nombre, f"no se pudo conectar: {ultimo_error}")

    @staticmethod
    def _safe_json(response: httpx.Response) -> Any:
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Any:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> Any:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Any:
        return await self.request("DELETE", path, **kwargs)
