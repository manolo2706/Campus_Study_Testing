"""Endpoints del servicio de Tareas (operaciones 1 a 7 del contrato v1.0)."""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app import servicios
from app.config import config
from app.database import obtener_bd
from app.esquemas import CambioEstado, TareaActualizar, TareaCrear, tarea_resumida
from app.notificaciones import notificar
from app.respuestas import exito
from app.seguridad import verificar_token
from app.utilidades import fecha_hora_texto

router = APIRouter(prefix="/api/v1/tareas", tags=["Tareas"], dependencies=[Depends(verificar_token)])


# --- Operación 7: debe ir antes de /{tarea_id} para que no la capture esa ruta ---
@router.get("/resumen")
def obtener_resumen(usuario_id: int = Query(gt=0), bd: Session = Depends(obtener_bd)):
    """Resumen de tareas por estado, consumido por el servicio de Estadísticas (#4)."""
    return exito(servicios.resumen(bd, usuario_id), "Resumen generado correctamente")


# --- Operación 1 ---
@router.post("")
async def crear_tarea(
    datos: TareaCrear,
    bd: Session = Depends(obtener_bd),
    idempotencia: str | None = Header(
        default=None,
        alias="X-Idempotency-Key",
        description="Clave opcional para que un reintento no cree la tarea dos veces",
    ),
):
    # Si el cliente reintenta con la misma clave, se devuelve la tarea ya creada
    # en lugar de crear una nueva.
    if idempotencia:
        existente = servicios.buscar_por_clave(bd, idempotencia)
        if existente is not None:
            return exito(
                servicios.como_diccionario(existente),
                "La tarea ya había sido creada con esta clave de idempotencia",
                200,
            )

    await servicios.validar_referencias(datos)
    tarea = servicios.crear(bd, datos)
    servicios.registrar_clave(bd, idempotencia, tarea.tarea_id)
    await notificar(bd, tarea, "tarea_creada")
    return exito(servicios.como_diccionario(tarea), "Tarea creada correctamente", 201)


# --- Operación 3 ---
@router.get("")
def listar_tareas(
    usuario_id: int | None = Query(default=None, gt=0),
    materia_id: int | None = Query(default=None, gt=0),
    grupo_id: int | None = Query(default=None, gt=0),
    estado: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=100),
    bd: Session = Depends(obtener_bd),
):
    total, filas = servicios.listar(bd, usuario_id, materia_id, grupo_id, estado, pagina, tamano)
    datos = {
        "total": total,
        "pagina": pagina,
        "tamano": tamano,
        "tareas": [tarea_resumida(t) for t in filas],
    }
    return exito(datos, "Consulta realizada correctamente")


# --- Operación 2 ---
@router.get("/{tarea_id}")
def consultar_tarea(tarea_id: int, bd: Session = Depends(obtener_bd)):
    tarea = servicios.obtener_tarea(bd, tarea_id)
    return exito(servicios.como_diccionario(tarea), "Consulta realizada correctamente")


# --- Operación 4 ---
@router.put("/{tarea_id}")
async def actualizar_tarea(tarea_id: int, datos: TareaActualizar, bd: Session = Depends(obtener_bd)):
    tarea = servicios.obtener_tarea(bd, tarea_id)
    tarea, cambio_fecha = servicios.actualizar(bd, tarea, datos)
    if cambio_fecha:
        await notificar(bd, tarea, "tarea_actualizada")
    return exito(servicios.como_diccionario(tarea), "Tarea actualizada correctamente")


# --- Operación 5 ---
@router.put("/{tarea_id}/estado")
def cambiar_estado(tarea_id: int, datos: CambioEstado, bd: Session = Depends(obtener_bd)):
    tarea = servicios.obtener_tarea(bd, tarea_id)
    tarea = servicios.cambiar_estado(bd, tarea, datos.estado)
    return exito(
        {
            "tarea_id": tarea.tarea_id,
            "estado": tarea.estado,
            "fecha_actualizacion": fecha_hora_texto(tarea.fecha_actualizacion),
        },
        "Estado actualizado correctamente",
    )


# --- Operación 6 ---
@router.delete("/{tarea_id}")
async def cancelar_tarea(tarea_id: int, bd: Session = Depends(obtener_bd)):
    tarea = servicios.obtener_tarea(bd, tarea_id)
    tarea = servicios.cancelar(bd, tarea)
    await notificar(bd, tarea, "tarea_cancelada")
    return exito(
        {"tarea_id": tarea.tarea_id, "estado": tarea.estado},
        "Tarea cancelada correctamente",
    )
