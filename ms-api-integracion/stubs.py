USUARIOS = {
    25: {
        "usuario_id": 25,
        "nombre": "Ana Milena Rojas",
        "correo": "estudiante@univer.edu.co",
        "rol": "estudiante",
        "estado": "activo",
        "habilidades": ["Python", "Redes", "Docker"],
    },
    30: {
        "usuario_id": 30,
        "nombre": "Luis Perez",
        "correo": "luis.perez@univer.edu.co",
        "rol": "estudiante",
        "estado": "activo",
        "habilidades": ["Python", "Docker"],
    },
    41: {
        "usuario_id": 41,
        "nombre": "Maria Gomez",
        "correo": "maria.gomez@univer.edu.co",
        "rol": "estudiante",
        "estado": "activo",
        "habilidades": ["Python", "Java"],
    },
    52: {
        "usuario_id": 52,
        "nombre": "Carlos Diaz",
        "correo": "carlos.diaz@univer.edu.co",
        "rol": "estudiante",
        "estado": "activo",
        "habilidades": ["IA", "Redes"],
    },
}

MATERIAS = {
    5: {"materia_id": 5, "nombre": "Sistemas Distribuidos", "codigo": "SD-301", "semestre": 6, "creditos": 3},
    8: {"materia_id": 8, "nombre": "Bases de Datos", "codigo": "BD-302", "semestre": 6, "creditos": 4},
}

INSCRIPCIONES = {
    25: [5, 8],
    30: [5],
    41: [5],
    52: [8],
}

TAREAS = {
    101: {
        "tarea_id": 101,
        "usuario_id": 25,
        "materia_id": 5,
        "titulo": "Taller de microservicios",
        "descripcion": "Disenar el contrato REST",
        "fecha_entrega": "2026-09-30",
        "hora_entrega": "23:59",
        "estado": "pendiente",
    },
    102: {
        "tarea_id": 102,
        "usuario_id": 25,
        "materia_id": 8,
        "titulo": "Modelo entidad-relacion",
        "descripcion": "Normalizar hasta 3FN",
        "fecha_entrega": "2026-10-05",
        "hora_entrega": "18:00",
        "estado": "en_progreso",
    },
}

GRUPOS = {
    7: {
        "grupo_id": 7,
        "materia_id": 5,
        "nombre": "Equipo Alpha",
        "integrantes": [25, 30],
        "estado": "activo",
        "creado_por": 25,
        "fecha_creacion": "2026-09-10T10:00:00Z",
    },
}

NOTIFICACIONES = {
    25: [
        {
            "notificacion_id": 1,
            "tipo": "recordatorio",
            "titulo": "Tarea proxima",
            "mensaje": "Taller de microservicios vence el 2026-09-30",
            "estado": "pendiente",
            "fecha_creacion": "2026-10-14 08:00:00",
        }
    ]
}

ESTADISTICAS_USUARIO = {
    "usuario_id": 25,
    "nombre": "Ana Milena Rojas",
    "periodo": "2026-10",
    "tareas": {"total": 2, "completadas": 0, "pendientes": 2, "vencidas": 0, "porcentaje_completado": 0.0},
    "grupos": {"total_grupos": 1, "grupos_activos": 1},
    "materias": [{"materia_id": 5, "nombre": "Sistemas Distribuidos", "tareas_completadas": 0, "tareas_total": 1}],
    "fecha_calculo": "2026-10-12",
}
