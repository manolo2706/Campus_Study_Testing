from typing import Any

from clients.base import ServiceClient
from core.config import settings


class MateriasClient(ServiceClient):
    def __init__(self) -> None:
        super().__init__("materias", settings.materias_url)

    async def listar(self, *, usuario_id: int | None = None, semestre: int | None = None, termino: str | None = None) -> list[dict]:
        if settings.stubs_enabled:
            import stubs

            if usuario_id is not None:
                return [stubs.MATERIAS[m] for m in stubs.INSCRIPCIONES.get(usuario_id, []) if m in stubs.MATERIAS]
            materias = list(stubs.MATERIAS.values())
            if semestre is not None:
                materias = [m for m in materias if m.get("semestre") == semestre]
            if termino:
                t = termino.lower()
                materias = [m for m in materias if t in m.get("nombre", "").lower() or t in str(m.get("codigo", "")).lower()]
            return materias

        params: dict[str, Any] = {}
        if usuario_id is not None:
            params["usuario_id"] = usuario_id
        if semestre is not None:
            params["semestre"] = semestre
        if termino:
            params["termino"] = termino
        data = await self.get(
            "/api/v1/materias",
            params=params or None,
            cache_key=f"materias:{usuario_id}:{semestre}:{termino}",
        )
        return data or []

    async def detalle(self, materia_id: int) -> dict | None:
        if settings.stubs_enabled:
            import stubs

            return stubs.MATERIAS.get(materia_id)
        data = await self.get(f"/api/v1/materias/{materia_id}", cache_key=f"materia:{materia_id}")
        return data if data else None

    async def materias_estudiante(self, usuario_id: int) -> list[dict]:
        return await self.listar(usuario_id=usuario_id)


materias_client = MateriasClient()
