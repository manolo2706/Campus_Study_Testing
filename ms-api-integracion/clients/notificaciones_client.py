from datetime import datetime

from clients.base import ServiceClient
from core.config import settings


class NotificacionesClient(ServiceClient):
    def __init__(self) -> None:
        super().__init__("notificaciones", settings.notificaciones_url)

    @staticmethod
    def _normalizar(n: dict, usuario_id: int) -> dict:
        estado = str(n.get("estado") or "").lower()
        return {
            "notificacion_id": n.get("notificacion_id") or n.get("_id") or n.get("id"),
            "usuario_id": usuario_id,
            "tipo": n.get("tipo"),
            "titulo": n.get("titulo"),
            "mensaje": n.get("mensaje"),
            "leida": estado in {"leida", "leido", "realizado", "visto"},
            "estado": n.get("estado"),
            "creada_en": n.get("fecha_creacion") or n.get("createdAt"),
        }

    async def listar(self, usuario_id: int, *, solo_no_leidas: bool = False) -> list[dict]:
        if settings.stubs_enabled:
            import stubs

            notificaciones = [self._normalizar(n, usuario_id) for n in stubs.NOTIFICACIONES.get(usuario_id, [])]
        else:
            data = await self.get(f"/api/v1/notification/{usuario_id}")
            if not isinstance(data, list):
                return []
            notificaciones = [self._normalizar(n, usuario_id) for n in data]
        if solo_no_leidas:
            notificaciones = [n for n in notificaciones if not n["leida"]]
        return notificaciones

    async def crear(
        self,
        usuario_id: int,
        *,
        tipo: str,
        titulo: str,
        mensaje: str,
        estado: str = "pendiente",
        referencia_id: int | None = None,
        fecha_creacion: str | None = None,
    ) -> dict:
        body = {
            "usuario_id": usuario_id,
            "tipo": tipo,
            "titulo": titulo,
            "mensaje": mensaje,
            "estado": estado,
            "fecha_creacion": fecha_creacion or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if referencia_id is not None:
            body["referencia_id"] = referencia_id
        if settings.stubs_enabled:
            import stubs

            stubs.NOTIFICACIONES.setdefault(usuario_id, []).append(
                {**body, "notificacion_id": len(stubs.NOTIFICACIONES[usuario_id]) + 1}
            )
            return {"codigo": 201, "mensaje": "Notificacion creada correctamente", "fecha_creacion": body["fecha_creacion"]}
        return await self.post("/api/v1/notification/create-notifications", json=body)

    async def marcar_leida(self, notificacion_id: int) -> dict:
        if settings.stubs_enabled:
            import stubs

            for notificaciones in stubs.NOTIFICACIONES.values():
                for n in notificaciones:
                    if n.get("notificacion_id") == notificacion_id:
                        n["estado"] = "leida"
                        return {"notificacion_id": notificacion_id, "leida": True}
        from core.errors import ApiError

        raise ApiError(501, "Operacion no soportada por el proveedor", "Notificaciones no expone marcar como leida")

    async def marcar_todas(self, usuario_id: int) -> dict:
        if settings.stubs_enabled:
            import stubs

            for n in stubs.NOTIFICACIONES.get(usuario_id, []):
                n["estado"] = "leida"
            return {"usuario_id": usuario_id, "marcadas": len(stubs.NOTIFICACIONES.get(usuario_id, []))}
        from core.errors import ApiError

        raise ApiError(501, "Operacion no soportada por el proveedor", "Notificaciones no expone marcar-todas")


notificaciones_client = NotificacionesClient()
