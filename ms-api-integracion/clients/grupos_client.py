from typing import Any

from clients.base import ServiceClient
from core.config import settings
from core.errors import NotFound


class GruposClient(ServiceClient):
    def __init__(self) -> None:
        super().__init__("grupos", settings.grupos_url)

    async def listar(self, *, materia_id: int | None = None, headers: dict | None = None) -> list[dict]:
        if settings.stubs_enabled:
            import stubs

            grupos = list(stubs.GRUPOS.values())
            if materia_id is not None:
                grupos = [g for g in grupos if g.get("materia_id") == materia_id]
            return grupos

        params: dict[str, Any] = {}
        if materia_id is not None:
            params["materia_id"] = materia_id
        data = await self.get("/api/v1/grupos", params=params or None, headers=headers)
        return data or []

    async def detalle(self, grupo_id: int, headers: dict | None = None) -> dict | None:
        if settings.stubs_enabled:
            import stubs

            grupo = stubs.GRUPOS.get(grupo_id)
            if grupo is None:
                raise NotFound("Grupo no encontrado", f"grupo_id={grupo_id} no existe")
            detalle = dict(grupo)
            detalle["integrantes"] = [
                {"usuario_id": uid, "rol": "miembro", "unido_en": grupo.get("fecha_creacion")}
                for uid in grupo.get("integrantes", [])
            ]
            return detalle
        data = await self.get(f"/api/v1/grupos/{grupo_id}", headers=headers)
        if not data:
            raise NotFound("Grupo no encontrado", f"grupo_id={grupo_id} no existe")
        return data

    async def crear(self, body: dict, headers: dict | None = None) -> dict:
        if settings.stubs_enabled:
            import stubs
            from events.publisher import ahora_utc

            nuevo_id = max(stubs.GRUPOS.keys(), default=0) + 1
            grupo = {
                "grupo_id": nuevo_id,
                "materia_id": body.get("materia_id"),
                "nombre": body.get("nombre"),
                "integrantes": body.get("integrantes", []),
                "estado": "activo",
                "creado_por": body.get("creado_por", 25),
                "fecha_creacion": ahora_utc(),
            }
            stubs.GRUPOS[nuevo_id] = grupo
            return grupo
        return await self.post("/api/v1/grupos", json=body, headers=headers)

    async def agregar_integrante(self, grupo_id: int, usuario_id: int, headers: dict | None = None) -> dict:
        if settings.stubs_enabled:
            import stubs

            grupo = stubs.GRUPOS.get(grupo_id)
            if grupo is None:
                raise NotFound("Grupo no encontrado", f"grupo_id={grupo_id} no existe")
            integrantes = grupo.setdefault("integrantes", [])
            if usuario_id not in integrantes:
                integrantes.append(usuario_id)
            return {"mensaje": "Integrante agregado correctamente", "integrante": {"usuario_id": usuario_id, "rol": "miembro"}}
        return await self.post(
            f"/api/v1/grupos/{grupo_id}/integrantes",
            json={"usuario_id": usuario_id},
            headers=headers,
        )

    async def retirar_integrante(self, grupo_id: int, usuario_id: int, headers: dict | None = None) -> None:
        if settings.stubs_enabled:
            import stubs

            grupo = stubs.GRUPOS.get(grupo_id)
            if grupo is None:
                raise NotFound("Grupo no encontrado", f"grupo_id={grupo_id} no existe")
            if usuario_id in grupo.get("integrantes", []):
                grupo["integrantes"].remove(usuario_id)
            return
        await self.delete(f"/api/v1/grupos/{grupo_id}/integrantes/{usuario_id}", headers=headers)

    async def grupos_de_usuario(self, usuario_id: int, headers: dict | None = None) -> list[dict]:
        grupos = await self.listar(headers=headers)
        resultado = []
        for grupo in grupos:
            integrantes = grupo.get("integrantes") or []
            ids = {i.get("usuario_id") if isinstance(i, dict) else i for i in integrantes}
            if usuario_id in ids or grupo.get("creado_por") == usuario_id:
                resultado.append(grupo)
        return resultado


grupos_client = GruposClient()
