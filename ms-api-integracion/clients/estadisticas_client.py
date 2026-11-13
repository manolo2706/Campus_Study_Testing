from typing import Any

from clients.base import ServiceClient
from core.config import settings


class EstadisticasClient(ServiceClient):
    def __init__(self) -> None:
        super().__init__("estadisticas", settings.estadisticas_url)

    async def usuario(self, usuario_id: int, *, periodo: str | None = None, materia_id: int | None = None) -> dict:
        if settings.stubs_enabled:
            import stubs

            datos = dict(stubs.ESTADISTICAS_USUARIO)
            datos["usuario_id"] = usuario_id
            if periodo:
                datos["periodo"] = periodo
            return datos
        params: dict[str, Any] = {}
        if periodo:
            params["periodo"] = periodo
        if materia_id is not None:
            params["materia_id"] = materia_id
        return await self.get(f"/api/v1/estadisticas/usuario/{usuario_id}", params=params or None)

    async def materia(self, materia_id: int, *, periodo: str | None = None) -> dict:
        if settings.stubs_enabled:
            return {
                "materia_id": materia_id,
                "nombre": "Sistemas Distribuidos",
                "periodo": periodo or "2026-10",
                "tareas": {"total": 2, "completadas": 1, "pendientes": 1},
                "grupos": {"total": 1},
                "fecha_calculo": "2026-10-12",
            }
        params = {"periodo": periodo} if periodo else None
        return await self.get(f"/api/v1/estadisticas/materia/{materia_id}", params=params)

    async def grupo(self, grupo_id: int) -> dict:
        if settings.stubs_enabled:
            return {
                "grupo_id": grupo_id,
                "nombre": "Equipo Alpha",
                "materia_id": 5,
                "integrantes": 2,
                "tareas": {"total": 1, "completadas": 0},
                "fecha_calculo": "2026-10-12",
            }
        return await self.get(f"/api/v1/estadisticas/grupo/{grupo_id}")

    async def publicar_evento(self, evento: str, payload: dict, *, version: str = "1.0", evento_id: str | None = None) -> dict:
        if settings.stubs_enabled:
            return {"aceptado": True, "duplicado": False, "evento_id": evento_id, "tipo": evento}
        body = {"evento": evento, "version": version, "payload": payload}
        if evento_id:
            body["evento_id"] = evento_id
        return await self.post("/api/v1/eventos", json=body)


estadisticas_client = EstadisticasClient()
