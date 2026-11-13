"""Validación del header Authorization (error 401 del contrato).

Hay dos escenarios posibles según lo que se acuerde en la reunión de integración:

1. El API Gateway (#5) valida el token y los servicios confían en él.
   -> VALIDAR_TOKEN_CON_USUARIOS=false (valor por defecto)
   Aquí solo se comprueba que el token venga presente y bien formado.

2. Cada servicio valida el token contra Usuarios (#8).
   -> VALIDAR_TOKEN_CON_USUARIOS=true
   Se llama al endpoint de validación y el resultado se guarda en caché.
"""
import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import contexto
from app.config import config
from app.errores import ErrorContrato, NoAutorizado

log = logging.getLogger("ms-tareas.seguridad")

esquema_token = HTTPBearer(
    auto_error=False,
    description="Token emitido por el servicio de Usuarios y autenticación (#8)",
)


async def verificar_token(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_token),
) -> str:
    if credenciales is None:
        raise NoAutorizado("Falta el header Authorization o no tiene el formato: Bearer <token>")

    token = credenciales.credentials.strip()
    if not token:
        raise NoAutorizado("El token no puede estar vacío")

    # Se guarda para reenviarlo a los otros servicios en esta misma petición.
    contexto.fijar_token(token)

    if config.validar_token_con_usuarios:
        from app.clientes import validar_token_remoto
        try:
            if not await validar_token_remoto(token):
                raise NoAutorizado("El token no es válido o ya venció")
        except NoAutorizado:
            raise
        except ErrorContrato:
            # Si Usuarios no responde no se puede afirmar que el token sea inválido.
            # Se deja pasar la petición y se registra, para no bloquear todo el
            # sistema por la caída de un servicio (principio de la sección J).
            log.warning(
                "No se pudo validar el token con Usuarios; se continúa | request_id=%s",
                contexto.request_id(),
            )

    return token
