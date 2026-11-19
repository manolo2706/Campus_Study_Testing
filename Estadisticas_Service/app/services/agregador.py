from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import GrupoProyeccion, MateriaProyeccion, MiembroGrupo, TareaProyeccion
from app.schemas import (
    EstadisticasGrupo,
    EstadisticasMateria,
    EstadisticasUsuario,
    GruposResumen,
    MateriaResumen,
    TareasResumen,
)
from app.services.tiempo import ahora, estado_efectivo, hoy_iso

# Un grupo está activo si tiene al menos una tarea sin cerrar
ESTADOS_ABIERTOS = {"pendiente", "en_progreso", "vencida"}


def _tareas(
    db: Session,
    usuario_id: int | None = None,
    materia_id: int | None = None,
    grupo_id: int | None = None,
    periodo: str | None = None,
) -> list[TareaProyeccion]:
    # Solo se filtra por lo que vino: None significa "sin filtro"
    criterios = {"usuario_id": usuario_id, "materia_id": materia_id, "grupo_id": grupo_id}
    consulta = db.query(TareaProyeccion).filter_by(**{k: v for k, v in criterios.items() if v is not None})

    if periodo:
        inicio, fin = _rango_del_mes(periodo)
        consulta = consulta.filter(TareaProyeccion.fecha_entrega >= inicio, TareaProyeccion.fecha_entrega < fin)

    return consulta.all()


def _rango_del_mes(periodo: str) -> tuple[datetime, datetime]:
    """"2026-11" → (1 de noviembre, 1 de diciembre): el inicio entra, el fin no."""
    inicio = datetime.strptime(periodo, "%Y-%m")
    return inicio, (inicio + timedelta(days=32)).replace(day=1)


def resumen_tareas(tareas: list[TareaProyeccion], momento: datetime) -> TareasResumen:
    estados = [estado_efectivo(t.estado, t.fecha_entrega, momento) for t in tareas]
    estados = [e for e in estados if e != "cancelada"]

    total = len(estados)
    completadas = estados.count("completada")
    vencidas = estados.count("vencida")

    return TareasResumen(
        total=total,
        completadas=completadas,
        pendientes=total - completadas - vencidas,  # pendiente + en_progreso (contrato I.6)
        vencidas=vencidas,
        porcentaje_completado=round(completadas / total * 100, 1) if total else 0.0,
    )


def _grupos_activos(tareas: list[TareaProyeccion], momento: datetime) -> set[int]:
    return {
        t.grupo_id
        for t in tareas
        if t.grupo_id and estado_efectivo(t.estado, t.fecha_entrega, momento) in ESTADOS_ABIERTOS
    }


def _materias_usuario(db: Session, tareas: list[TareaProyeccion], momento: datetime) -> list[MateriaResumen]:
    por_materia: dict[int, list[TareaProyeccion]] = {}
    for tarea in tareas:
        por_materia.setdefault(tarea.materia_id, []).append(tarea)

    # Una sola consulta para todos los nombres, no una por materia
    nombres = {
        m.id: m.nombre
        for m in db.query(MateriaProyeccion).filter(MateriaProyeccion.id.in_(por_materia))
    }

    resultado = []
    for materia_id, items in por_materia.items():
        conteo = resumen_tareas(items, momento)
        resultado.append(MateriaResumen(
            materia_id=materia_id,
            nombre=nombres.get(materia_id) or f"Materia {materia_id}",
            tareas_completadas=conteo.completadas,
            tareas_total=conteo.total,
        ))
    return sorted(resultado, key=lambda m: m.tareas_total, reverse=True)


def estadisticas_usuario(
    db: Session,
    usuario_id: int,
    nombre: str,
    periodo: str | None = None,
    materia_id: int | None = None,
) -> EstadisticasUsuario:
    momento = ahora()
    tareas = _tareas(db, usuario_id=usuario_id, materia_id=materia_id, periodo=periodo)
    mis_grupos = {m.grupo_id for m in db.query(MiembroGrupo).filter_by(usuario_id=usuario_id)}

    return EstadisticasUsuario(
        usuario_id=usuario_id,
        nombre=nombre,
        periodo=periodo,
        tareas=resumen_tareas(tareas, momento),
        grupos=GruposResumen(
            total_grupos=len(mis_grupos),
            grupos_activos=len(_grupos_activos(tareas, momento) & mis_grupos),
        ),
        materias=_materias_usuario(db, tareas, momento),
        fecha_calculo=hoy_iso(),
    )


def estadisticas_materia(
    db: Session,
    materia_id: int,
    usuario_id: int,
    periodo: str | None = None,
) -> EstadisticasMateria | None:
    if not _puede_ver_materia(db, materia_id, usuario_id):
        return None

    momento = ahora()
    materia = db.get(MateriaProyeccion, materia_id)
    tareas = _tareas(db, materia_id=materia_id, periodo=periodo)
    grupos = db.query(GrupoProyeccion).filter_by(materia_id=materia_id).count()

    return EstadisticasMateria(
        materia_id=materia_id,
        nombre=materia.nombre if materia else f"Materia {materia_id}",
        nrc=materia.nrc if materia else None,
        periodo=periodo,
        tareas=resumen_tareas(tareas, momento),
        grupos=GruposResumen(total_grupos=grupos, grupos_activos=len(_grupos_activos(tareas, momento))),
        fecha_calculo=hoy_iso(),
    )


def estadisticas_grupo(db: Session, grupo_id: int, usuario_id: int) -> EstadisticasGrupo | None:
    grupo = db.get(GrupoProyeccion, grupo_id)
    if not grupo or not _es_integrante(db, grupo_id, usuario_id):
        return None

    return EstadisticasGrupo(
        grupo_id=grupo_id,
        nombre=grupo.nombre,
        materia_id=grupo.materia_id,
        integrantes=db.query(MiembroGrupo).filter_by(grupo_id=grupo_id).count(),
        tareas=resumen_tareas(_tareas(db, grupo_id=grupo_id), ahora()),
        fecha_calculo=hoy_iso(),
    )


# ---------- Quién puede ver qué (si no puede, la misma respuesta que "no existe") ----------

def _es_integrante(db: Session, grupo_id: int, usuario_id: int) -> bool:
    return db.query(MiembroGrupo.id).filter_by(grupo_id=grupo_id, usuario_id=usuario_id).first() is not None


def _puede_ver_materia(db: Session, materia_id: int, usuario_id: int) -> bool:
    """La materia es suya (tiene tareas en ella) o la comparte en un grupo."""
    tiene_tareas = db.query(TareaProyeccion.id).filter_by(materia_id=materia_id, usuario_id=usuario_id).first()
    en_grupo = (
        db.query(MiembroGrupo.id)
        .join(GrupoProyeccion, GrupoProyeccion.id == MiembroGrupo.grupo_id)
        .filter(GrupoProyeccion.materia_id == materia_id, MiembroGrupo.usuario_id == usuario_id)
        .first()
    )
    return tiene_tareas is not None or en_grupo is not None