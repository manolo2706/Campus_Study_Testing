from clients.auth_client import auth_client
from clients.estadisticas_client import estadisticas_client
from clients.grupos_client import grupos_client
from clients.materias_client import materias_client
from clients.notificaciones_client import notificaciones_client
from clients.tareas_client import tareas_client

__all__ = [
    "auth_client",
    "materias_client",
    "tareas_client",
    "grupos_client",
    "notificaciones_client",
    "estadisticas_client",
]
