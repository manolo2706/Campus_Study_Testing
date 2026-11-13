from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Header
from jwt import InvalidTokenError

from core.config import settings
from core.errors import ApiError


@dataclass
class Usuario:
    usuario_id: int | None
    email: str | None
    rol: str | None
    claims: dict
    token: str = ""

    @property
    def es_admin(self) -> bool:
        return self.rol == "admin"


def decode_token(token: str) -> Usuario:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=settings.jwt_algorithm_list)
    except InvalidTokenError:
        raise ApiError(401, "No autenticado", "token invalido o expirado")

    sub = claims.get("sub")
    try:
        usuario_id = int(sub) if sub is not None else None
    except (TypeError, ValueError):
        usuario_id = None

    return Usuario(
        usuario_id=usuario_id,
        email=claims.get("email"),
        rol=claims.get("rol"),
        claims=claims,
        token=token,
    )


async def require_token(authorization: str | None = Header(default=None)) -> Usuario:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "No autenticado", "token no proporcionado")
    return decode_token(authorization.replace("Bearer ", "", 1).strip())


async def optional_token(authorization: str | None = Header(default=None)) -> Usuario | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return decode_token(authorization.replace("Bearer ", "", 1).strip())


def crear_token(usuario_id: int, email: str | None, rol: str | None, *, expira_horas: int = 24) -> str:
    ahora = datetime.now(timezone.utc)
    claims = {
        "sub": str(usuario_id),
        "email": email,
        "rol": rol,
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + timedelta(hours=expira_horas)).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm_list[0])


def headers_to(usuario: Usuario | None, servicio: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    if usuario is None:
        return headers
    if servicio == "grupos" and settings.grupos_auth_mode == "demo_id" and usuario.usuario_id is not None:
        headers["Authorization"] = f"Bearer {usuario.usuario_id}"
    elif usuario.token:
        headers["Authorization"] = f"Bearer {usuario.token}"
    elif settings.servicio_token:
        headers["Authorization"] = f"Bearer {settings.servicio_token}"
    return headers
