"""Lógica del servicio de Tareas, siguiendo las operaciones 1 a 7 del contrato."""
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.clientes import consultar_grupo, consultar_materia, consultar_usuario
from app.errores import ErrorInterno, NoEncontrado, SolicitudIncorrecta
from app.esquemas import TRANSICIONES, tarea_completa
from app.models import PeticionIdempotente, Tarea
from app.utilidades import FORMATO_FECHA, ahora, hoy
from datetime import datetime

log = logging.getLogger("ms-tareas.servicios")


async def validar_referencias(datos) -> None:
    """Consulta a Usuarios, Materias y Grupos.

    Si el proveedor responde 404, el error está en los datos enviados: se devuelve 400.
    Si el proveedor no responde, el cliente HTTP lanza 503 y la tarea no se crea.
    """
    usuario = await consultar_usuario(datos.usuario_id)
    if usuario is None:
        raise SolicitudIncorrecta(f"El usuario_id {datos.usuario_id} no existe")
    if usuario.get("activo") is False:
        raise SolicitudIncorrecta(f"El usuario_id {datos.usuario_id} no está activo")

    materia = await consultar_materia(datos.materia_id)
    if materia is None:
        raise SolicitudIncorrecta(f"La materia_id {datos.materia_id} no existe")

    if datos.grupo_id:
        grupo = await consultar_grupo(datos.grupo_id)
        if grupo is None:
            raise SolicitudIncorrecta(f"El grupo_id {datos.grupo_id} no existe")
        integrantes = grupo.get("integrantes") or []
        if integrantes and datos.usuario_id not in integrantes:
            raise SolicitudIncorrecta(
                f"El usuario_id {datos.usuario_id} no es integrante del grupo {datos.grupo_id}"
            )


def _guardar(bd: Session, tarea: Tarea) -> Tarea:
    try:
        bd.add(tarea)
        bd.commit()
        bd.refresh(tarea)
        return tarea
    except SQLAlchemyError:
        bd.rollback()
        log.exception("Error al guardar en la base de datos")
        raise ErrorInterno("No fue posible guardar la tarea")


def obtener_tarea(bd: Session, tarea_id: int) -> Tarea:
    tarea = bd.query(Tarea).filter(Tarea.tarea_id == tarea_id).first()
    if tarea is None:
        raise NoEncontrado(f"La tarea con tarea_id {tarea_id} no existe")
    return tarea


def crear(bd: Session, datos) -> Tarea:
    tarea = Tarea(
        titulo=datos.titulo.strip(),
        descripcion=datos.descripcion,
        usuario_id=datos.usuario_id,
        materia_id=datos.materia_id,
        grupo_id=datos.grupo_id,
        fecha_entrega=datetime.strptime(datos.fecha_entrega, FORMATO_FECHA).date(),
        hora_entrega=datos.hora_entrega,
        prioridad=datos.prioridad,
        estado="pendiente",
        fecha_creacion=ahora(),
        fecha_actualizacion=ahora(),
    )
    return _guardar(bd, tarea)


def listar(bd: Session, usuario_id, materia_id, grupo_id, estado, pagina, tamano):
    if not any([usuario_id, materia_id, grupo_id]):
        raise SolicitudIncorrecta(
            "Debe enviar al menos uno de los filtros: usuario_id, materia_id o grupo_id"
        )
    consulta = bd.query(Tarea)
    if usuario_id:
        consulta = consulta.filter(Tarea.usuario_id == usuario_id)
    if materia_id:
        consulta = consulta.filter(Tarea.materia_id == materia_id)
    if grupo_id:
        consulta = consulta.filter(Tarea.grupo_id == grupo_id)
    if estado:
        consulta = consulta.filter(Tarea.estado == estado)

    total = consulta.count()
    filas = (
        consulta.order_by(Tarea.fecha_entrega.asc(), Tarea.tarea_id.asc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
        .all()
    )
    return total, filas


def actualizar(bd: Session, tarea: Tarea, datos) -> tuple[Tarea, bool]:
    cambio_fecha = False
    if datos.titulo is not None:
        tarea.titulo = datos.titulo.strip()
    if datos.descripcion is not None:
        tarea.descripcion = datos.descripcion
    if datos.fecha_entrega is not None:
        tarea.fecha_entrega = datetime.strptime(datos.fecha_entrega, FORMATO_FECHA).date()
        cambio_fecha = True
    if datos.hora_entrega is not None:
        tarea.hora_entrega = datos.hora_entrega
    if datos.prioridad is not None:
        tarea.prioridad = datos.prioridad
    tarea.fecha_actualizacion = ahora()
    return _guardar(bd, tarea), cambio_fecha


def cambiar_estado(bd: Session, tarea: Tarea, nuevo: str) -> Tarea:
    if nuevo == tarea.estado:
        raise SolicitudIncorrecta(f"La tarea ya se encuentra en estado {nuevo}")
    if nuevo not in TRANSICIONES[tarea.estado]:
        raise SolicitudIncorrecta(
            f"No se permite pasar del estado {tarea.estado} a {nuevo}"
        )
    tarea.estado = nuevo
    tarea.fecha_actualizacion = ahora()
    return _guardar(bd, tarea)


def cancelar(bd: Session, tarea: Tarea) -> Tarea:
    """Eliminación lógica: la tarea no se borra, pasa a estado cancelada."""
    if tarea.estado == "cancelada":
        raise SolicitudIncorrecta("La tarea ya está cancelada")
    tarea.estado = "cancelada"
    tarea.fecha_actualizacion = ahora()
    return _guardar(bd, tarea)


def resumen(bd: Session, usuario_id: int) -> dict:
    filas = bd.query(Tarea).filter(Tarea.usuario_id == usuario_id).all()
    abiertas = ("pendiente", "en_progreso")
    return {
        "usuario_id": usuario_id,
        "total": len(filas),
        "pendientes": sum(1 for t in filas if t.estado == "pendiente"),
        "en_progreso": sum(1 for t in filas if t.estado == "en_progreso"),
        "completadas": sum(1 for t in filas if t.estado == "completada"),
        "canceladas": sum(1 for t in filas if t.estado == "cancelada"),
        "vencidas": sum(1 for t in filas if t.estado in abiertas and t.fecha_entrega < hoy()),
    }


def como_diccionario(tarea: Tarea) -> dict:
    return tarea_completa(tarea)


# ---------------------------------------------------------------------------
# Idempotencia: evita duplicar una tarea cuando el cliente reintenta
# ---------------------------------------------------------------------------
def buscar_por_clave(bd: Session, clave: str):
    """Devuelve la tarea ya creada con esa clave de idempotencia, si existe."""
    if not clave:
        return None
    registro = (
        bd.query(PeticionIdempotente)
        .filter(PeticionIdempotente.clave == clave)
        .first()
    )
    if registro is None:
        return None
    return bd.query(Tarea).filter(Tarea.tarea_id == registro.tarea_id).first()


def registrar_clave(bd: Session, clave: str, tarea_id: int) -> None:
    if not clave:
        return
    try:
        bd.add(PeticionIdempotente(clave=clave, tarea_id=tarea_id, fecha_creacion=ahora()))
        bd.commit()
    except SQLAlchemyError:
        # Que falle el registro de la clave no debe tumbar la creación de la tarea.
        bd.rollback()
        log.warning("No se pudo registrar la clave de idempotencia %s", clave)


def limpiar_claves_vencidas(bd: Session, horas: int) -> int:
    from datetime import timedelta
    limite = ahora() - timedelta(hours=horas)
    borradas = (
        bd.query(PeticionIdempotente)
        .filter(PeticionIdempotente.fecha_creacion < limite)
        .delete(synchronize_session=False)
    )
    bd.commit()
    return borradas
