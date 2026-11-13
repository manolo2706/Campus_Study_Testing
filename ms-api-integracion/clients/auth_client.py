from clients.base import ServiceClient
from core.config import settings


class AuthClient(ServiceClient):
    def __init__(self) -> None:
        super().__init__("auth", settings.auth_url)

    async def login(self, correo: str, password: str) -> dict:
        if settings.stubs_enabled:
            import stubs
            from core.security import crear_token

            for usuario in stubs.USUARIOS.values():
                if usuario["correo"].lower() == correo.lower():
                    token = crear_token(usuario["usuario_id"], usuario["correo"], usuario["rol"])
                    return {
                        "token": token,
                        "refresh_token": token,
                        "usuario_id": usuario["usuario_id"],
                        "nombre": usuario["nombre"],
                        "correo": usuario["correo"],
                        "rol": usuario["rol"],
                        "tipo_token": "Bearer",
                        "expira_en": 86400,
                    }
            from core.errors import ApiError

            raise ApiError(401, "Credenciales invalidas", "correo o password incorrectos")

        data = await self.post("/api/v1/auth/login", json={"email": correo, "password": password})
        return self._normalizar_auth(data or {})

    async def registro(self, nombre: str, correo: str, password: str) -> dict:
        if settings.stubs_enabled:
            import stubs

            nuevo_id = max(stubs.USUARIOS.keys(), default=0) + 1
            usuario = {
                "usuario_id": nuevo_id,
                "nombre": nombre,
                "correo": correo,
                "rol": "estudiante",
                "estado": "activo",
                "habilidades": [],
            }
            stubs.USUARIOS[nuevo_id] = usuario
            return usuario
        data = await self.post(
            "/api/v1/auth/registro",
            json={"nombre": nombre, "email": correo, "password": password},
        )
        return self._normalizar_usuario(data or {})

    async def get_usuario(self, usuario_id: int) -> dict | None:
        if settings.stubs_enabled:
            import stubs

            return stubs.USUARIOS.get(usuario_id)
        data = await self.get(f"/api/v1/users/{usuario_id}")
        if not data:
            return None
        return self._normalizar_usuario(data)

    @staticmethod
    def _normalizar_auth(data: dict) -> dict:
        return {
            "token": data.get("token"),
            "refresh_token": data.get("refresh_token"),
            "usuario_id": data.get("usuario_id"),
            "nombre": data.get("nombre"),
            "correo": data.get("email") or data.get("correo"),
            "rol": data.get("rol"),
            "tipo_token": data.get("tipo_token", "Bearer"),
            "expira_en": data.get("expira_en"),
        }

    @staticmethod
    def _normalizar_usuario(data: dict) -> dict:
        return {
            "usuario_id": data.get("usuario_id"),
            "nombre": data.get("nombre"),
            "correo": data.get("email") or data.get("correo"),
            "rol": data.get("rol"),
            "estado": data.get("estado"),
            "habilidades": data.get("habilidades") or [],
            "fecha_registro": data.get("fecha_registro"),
        }


auth_client = AuthClient()
