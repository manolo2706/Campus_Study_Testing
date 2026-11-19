from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import settings

bearer = HTTPBearer()


class UsuarioToken(BaseModel):
    usuario_id: int
    nombre: str


def usuario_actual(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]) -> UsuarioToken:
    """Valida el JWT de users-auth (HS256 + JWT_SECRET compartido) y saca quién es."""
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
        return UsuarioToken(usuario_id=int(payload["sub"]), nombre=payload.get("nombre", ""))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail={"codigo": 401, "mensaje": "Token inválido o expirado"})


UsuarioActual = Annotated[UsuarioToken, Depends(usuario_actual)]