from fastapi import APIRouter, Depends, Response

from clients import auth_client
from core.envelope import ok
from core.errors import NotFound
from core.security import Usuario, crear_token, require_token
from schemas.auth import LoginRequest, RegistroRequest

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post("/login")
async def login(body: LoginRequest) -> dict:
    return ok(await auth_client.login(body.correo, body.password))


@router.post("/registro")
async def registro(body: RegistroRequest) -> dict:
    return ok(await auth_client.registro(body.nombre, body.correo, body.password))


@router.post("/refresh")
async def refresh(usuario: Usuario = Depends(require_token)) -> dict:
    token = crear_token(usuario.usuario_id or 0, usuario.email, usuario.rol)
    return ok({"token": token, "tipo_token": "Bearer", "expira_en": 86400})


@router.post("/logout", status_code=204)
async def logout(usuario: Usuario = Depends(require_token)) -> Response:
    return Response(status_code=204)


@router.get("/me")
async def me(usuario: Usuario = Depends(require_token)) -> dict:
    perfil = None
    if usuario.usuario_id is not None:
        perfil = await auth_client.get_usuario(usuario.usuario_id)
    if perfil is None:
        if usuario.usuario_id is None:
            raise NotFound("Perfil no encontrado", "el token no contiene usuario_id")
        perfil = {
            "usuario_id": usuario.usuario_id,
            "nombre": None,
            "correo": usuario.email,
            "rol": usuario.rol,
            "estado": None,
            "habilidades": [],
        }
    return ok(perfil)
