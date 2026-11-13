"""Traduce las respuestas de los otros microservicios al formato que espera Tareas.

En el contrato quedó acordado que Usuarios devolvería usuario_id, nombre y activo;
Materias, materia_id y nombre; y Grupos, grupo_id, nombre e integrantes. En la
práctica cada equipo puede entregar esos mismos datos con otro nombre o envueltos
en otra estructura, y nuestro servicio no debería romperse por eso.

Este módulo busca el dato por varios nombres posibles y siempre devuelve la
estructura del contrato. Si un equipo usa un nombre que no está contemplado, se
agrega a la lista correspondiente y no hay que tocar nada más.
"""
import logging

log = logging.getLogger("ms-tareas.adaptadores")

# Claves con las que un servicio podría entregar cada dato
ID_USUARIO = ("usuario_id", "usuarioId", "user_id", "userId", "id_usuario", "idUsuario", "id")
ID_MATERIA = ("materia_id", "materiaId", "subject_id", "id_materia", "idMateria", "id", "codigo")
ID_GRUPO = ("grupo_id", "grupoId", "group_id", "id_grupo", "idGrupo", "id")
NOMBRE = ("nombre", "name", "nombres", "nombre_completo", "nombreCompleto", "full_name",
          "titulo", "descripcion")
ACTIVO = ("activo", "active", "is_active", "isActive", "habilitado", "enabled", "estado", "status")
INTEGRANTES = ("integrantes", "miembros", "members", "estudiantes", "usuarios",
               "participantes", "integrantes_ids", "usuarios_ids")

# Envolturas comunes: {"datos": {...}}, {"data": {...}}, {"result": {...}}
ENVOLTURAS = ("datos", "data", "result", "resultado", "payload", "content", "body", "item")

VERDADEROS = ("activo", "active", "true", "1", "si", "sí", "a", "habilitado", "enabled", "ok")
FALSOS = ("inactivo", "inactive", "false", "0", "no", "i", "deshabilitado", "disabled",
          "bloqueado", "suspendido", "eliminado")


def desenvolver(cuerpo):
    """Quita las envolturas hasta llegar al objeto con los datos."""
    visto = 0
    while isinstance(cuerpo, dict) and visto < 4:
        for clave in ENVOLTURAS:
            interno = cuerpo.get(clave)
            if isinstance(interno, (dict, list)) and interno:
                cuerpo = interno
                break
        else:
            break
        visto += 1
    # Algunos servicios devuelven una lista de un solo elemento
    if isinstance(cuerpo, list):
        cuerpo = cuerpo[0] if len(cuerpo) == 1 else None
    return cuerpo if isinstance(cuerpo, dict) else None


def _buscar(datos: dict, claves) -> object:
    """Busca la primera clave presente, sin importar mayúsculas ni guiones bajos."""
    for clave in claves:
        if clave in datos and datos[clave] is not None:
            return datos[clave]
    normalizado = {str(k).lower().replace("_", ""): v for k, v in datos.items()}
    for clave in claves:
        simple = clave.lower().replace("_", "")
        if normalizado.get(simple) is not None:
            return normalizado[simple]
    return None


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _booleano(valor, por_defecto=True):
    """Interpreta activo tanto si llega como booleano, como número o como texto."""
    if valor is None:
        return por_defecto
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    texto = str(valor).strip().lower()
    if texto in VERDADEROS:
        return True
    if texto in FALSOS:
        return False
    return por_defecto


def normalizar_usuario(cuerpo, usuario_id: int):
    datos = desenvolver(cuerpo)
    if datos is None:
        return None
    return {
        "usuario_id": _entero(_buscar(datos, ID_USUARIO)) or usuario_id,
        "nombre": _buscar(datos, NOMBRE) or "",
        # Si el servicio no informa el estado, se asume activo: el contrato dice
        # que la ausencia de un dato opcional no puede bloquear la operación.
        "activo": _booleano(_buscar(datos, ACTIVO), por_defecto=True),
    }


def normalizar_materia(cuerpo, materia_id: int):
    datos = desenvolver(cuerpo)
    if datos is None:
        return None
    return {
        "materia_id": _entero(_buscar(datos, ID_MATERIA)) or materia_id,
        "nombre": _buscar(datos, NOMBRE) or "",
    }


def _lista_integrantes(valor) -> list[int]:
    """Acepta [1,2,3], ["1","2"] o [{"usuario_id": 1}, {"id": 2}]."""
    if not isinstance(valor, list):
        return []
    salida = []
    for elemento in valor:
        if isinstance(elemento, dict):
            numero = _entero(_buscar(elemento, ID_USUARIO))
        else:
            numero = _entero(elemento)
        if numero is not None:
            salida.append(numero)
    return salida


def normalizar_grupo(cuerpo, grupo_id: int):
    datos = desenvolver(cuerpo)
    if datos is None:
        return None
    integrantes = _lista_integrantes(_buscar(datos, INTEGRANTES))
    if not integrantes:
        log.info(
            "El grupo %s no entregó la lista de integrantes; no se valida la pertenencia",
            grupo_id,
        )
    return {
        "grupo_id": _entero(_buscar(datos, ID_GRUPO)) or grupo_id,
        "nombre": _buscar(datos, NOMBRE) or "",
        "integrantes": integrantes,
    }


def renombrar_campos(evento: dict, mapa: dict) -> dict:
    """Renombra las claves del evento de notificación según lo acordado con el #7."""
    if not mapa:
        return evento
    return {mapa.get(clave, clave): valor for clave, valor in evento.items()}
