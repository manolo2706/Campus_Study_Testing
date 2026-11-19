from typing import Any

from clients.base import ServiceClient
from core.config import settings
from core.errors import NotFound


class TareasClient(ServiceClient):
    def __init__(self) -> None:
        super().__init__("tareas", settings.tareas_url)

    async def listar(
        self,
        *,
        usuario_id: int | None = None,
        materia_id: int | None = None,
        grupo_id: int | None = None,
        estado: str | None = None,
        fecha_limite: str | None = None,
        headers: dict | None = None,
    ) -> list[dict]:
        if settings.stubs_enabled:
            import stubs

            tareas = list(stubs.TAREAS.values())
            if usuario_id is not None:
                tareas = [t for t in tareas if t.get("usuario_id") == usuario_id]
            if materia_id is not None:
                tareas = [t for t in tareas if t.get("materia_id") == materia_id]
            if estado:
                tareas = [t for t in tareas if t.get("estado") == estado]
            if fecha_limite:
                tareas = [t for t in tareas if t.get("fecha_entrega") == fecha_limite]
            return tareas

        params: dict[str, Any] = {}
        for key, valor in (
            ("usuario_id", usuario_id),
            ("materia_id", materia_id),
            ("grupo_id", grupo_id),
            ("estado", estado),
            ("fecha_limite", fecha_limite),
        ):
            if valor is not None:
                params[key] = valor
        data = await self.get("/api/v1/tareas", params=params or None, headers=headers)
        return data or []

    async def detalle(self, tarea_id: int, headers: dict | None = None) -> dict | None:
        if settings.stubs_enabled:
            import stubs

            tarea = stubs.TAREAS.get(tarea_id)
            if tarea is None:
                raise NotFound("Tarea no encontrada", f"tarea_id={tarea_id} no existe")
            return tarea
        data = await self.get(f"/api/v1/tareas/{tarea_id}", headers=headers)
        if not data:
            raise NotFound("Tarea no encontrada", f"tarea_id={tarea_id} no existe")
        return data

    async def crear(self, body: dict, headers: dict | None = None) -> dict:
        if settings.stubs_enabled:
            import stubs

            nuevo_id = max(stubs.TAREAS.keys(), default=100) + 1
            tarea = {"tarea_id": nuevo_id, **body}
            stubs.TAREAS[nuevo_id] = tarea
            return tarea
        return await self.post("/api/v1/tareas", json=body, headers=headers)

    async def actualizar(self, tarea_id: int, body: dict, headers: dict | None = None) -> dict:
        if settings.stubs_enabled:
            import stubs

            tarea = stubs.TAREAS.get(tarea_id)
            if tarea is None:
                raise NotFound("Tarea no encontrada", f"tarea_id={tarea_id} no existe")
            tarea.update(body)
            return tarea
        return await self.put(f"/api/v1/tareas/{tarea_id}", json=body, headers=headers)

    async def eliminar(self, tarea_id: int, headers: dict | None = None) -> None:
        if settings.stubs_enabled:
            import stubs

            if tarea_id not in stubs.TAREAS:
                raise NotFound("Tarea no encontrada", f"tarea_id={tarea_id} no existe")
            stubs.TAREAS.pop(tarea_id)
            return
        await self.delete(f"/api/v1/tareas/{tarea_id}", headers=headers)


tareas_client = TareasClient()
