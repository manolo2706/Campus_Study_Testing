"""Casos de prueba de integración definidos en la sección L del contrato v1.0."""
from datetime import timedelta

from app.utilidades import hoy
from tests.conftest import CABECERAS

ENTREGA = (hoy() + timedelta(days=30)).strftime("%Y-%m-%d")


def nueva_tarea(**extra):
    datos = {
        "titulo": "Contrato de interfaz",
        "descripcion": "Documento del servicio de Tareas",
        "usuario_id": 692464,
        "materia_id": 12,
        "grupo_id": 1,
        "fecha_entrega": ENTREGA,
        "hora_entrega": "18:00",
        "prioridad": "alta",
    }
    datos.update(extra)
    return datos


def crear(cliente, **extra):
    return cliente.post("/api/v1/tareas", json=nueva_tarea(**extra), headers=CABECERAS)


# --- Caso 1 ---
def test_crear_tarea_valida(cliente):
    r = crear(cliente)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["exito"] is True
    assert cuerpo["datos"]["estado"] == "pendiente"
    assert cuerpo["datos"]["tarea_id"] > 0
    assert cuerpo["datos"]["fecha_creacion"] is not None


# --- Caso 2 ---
def test_crear_con_materia_inexistente(cliente):
    r = crear(cliente, materia_id=999999)
    assert r.status_code == 400
    assert r.json()["error"]["tipo"] == "SOLICITUD_INCORRECTA"
    assert "materia" in r.json()["error"]["mensaje"].lower()


# --- Caso 3 ---
def test_crear_con_usuario_fuera_del_grupo(cliente):
    r = crear(cliente, usuario_id=777)
    assert r.status_code == 400
    assert "integrante" in r.json()["error"]["mensaje"].lower()


def test_crear_con_usuario_inexistente(cliente):
    r = crear(cliente, usuario_id=999999, grupo_id=None)
    assert r.status_code == 400


# --- Caso 4: el proveedor no responde ---
def test_proveedor_sin_respuesta_devuelve_503(cliente, monkeypatch):
    from app import clientes, servicios
    from app.errores import ServicioNoDisponible

    async def caido(_):
        raise ServicioNoDisponible("El servicio de usuarios no está disponible")

    monkeypatch.setattr(servicios, "consultar_usuario", caido)
    r = crear(cliente)
    assert r.status_code == 503
    assert r.json()["error"]["tipo"] == "SERVICIO_NO_DISPONIBLE"


# --- Caso 5: Notificaciones caído, la tarea igual se crea ---
def test_notificaciones_caidas_no_bloquea(cliente, monkeypatch):
    from app import notificaciones
    from app.errores import ServicioNoDisponible
    from app.database import Sesion
    from app.models import EventoPendiente

    async def caido(_):
        raise ServicioNoDisponible("El servicio de notificaciones no está disponible")

    monkeypatch.setattr(notificaciones, "enviar_notificacion", caido)
    r = crear(cliente)
    assert r.status_code == 201

    bd = Sesion()
    assert bd.query(EventoPendiente).count() > 0
    bd.close()


# --- Caso 6 ---
def test_consultar_tarea_inexistente(cliente):
    r = cliente.get("/api/v1/tareas/999", headers=CABECERAS)
    assert r.status_code == 404
    assert r.json()["error"]["tipo"] == "RECURSO_NO_ENCONTRADO"


# --- Caso 7 ---
def test_resumen_para_estadisticas(cliente):
    crear(cliente)
    crear(cliente, titulo="Segunda tarea")
    r = cliente.get("/api/v1/tareas/resumen?usuario_id=692464", headers=CABECERAS)
    assert r.status_code == 200
    datos = r.json()["datos"]
    assert datos["total"] == 2
    assert datos["pendientes"] == 2
    assert set(datos) == {"usuario_id", "total", "pendientes", "en_progreso",
                          "completadas", "canceladas", "vencidas"}


# --- Caso 8 ---
def test_sin_token(cliente):
    r = cliente.get("/api/v1/tareas/1")
    assert r.status_code == 401
    assert r.json()["error"]["tipo"] == "NO_AUTORIZADO"


def test_token_mal_formado(cliente):
    r = cliente.get("/api/v1/tareas/1", headers={"Authorization": "token-suelto"})
    assert r.status_code == 401


# --- Reglas de datos y operaciones restantes ---
def test_listado_sin_filtros_devuelve_400(cliente):
    r = cliente.get("/api/v1/tareas", headers=CABECERAS)
    assert r.status_code == 400


def test_listado_sin_coincidencias_devuelve_lista_vacia(cliente):
    r = cliente.get("/api/v1/tareas?usuario_id=12345", headers=CABECERAS)
    assert r.status_code == 200
    assert r.json()["datos"]["tareas"] == []
    assert r.json()["datos"]["total"] == 0


def test_listado_con_paginacion(cliente):
    for i in range(3):
        crear(cliente, titulo=f"Tarea {i}")
    r = cliente.get("/api/v1/tareas?usuario_id=692464&pagina=1&tamano=2", headers=CABECERAS)
    datos = r.json()["datos"]
    assert datos["total"] == 3
    assert len(datos["tareas"]) == 2
    assert set(datos["tareas"][0]) == {"tarea_id", "titulo", "materia_id",
                                       "fecha_entrega", "estado"}


def test_fecha_con_formato_invalido(cliente):
    r = crear(cliente, fecha_entrega="15/12/2026")
    assert r.status_code == 400


def test_fecha_anterior_a_hoy(cliente):
    r = crear(cliente, fecha_entrega="2020-01-01")
    assert r.status_code == 400


def test_titulo_vacio(cliente):
    r = crear(cliente, titulo="")
    assert r.status_code == 400


def test_actualizar_tarea(cliente):
    tarea_id = crear(cliente).json()["datos"]["tarea_id"]
    r = cliente.put(f"/api/v1/tareas/{tarea_id}",
                    json={"titulo": "Contrato v1.1", "prioridad": "media"}, headers=CABECERAS)
    assert r.status_code == 200
    assert r.json()["datos"]["titulo"] == "Contrato v1.1"


def test_transicion_de_estado_valida(cliente):
    tarea_id = crear(cliente).json()["datos"]["tarea_id"]
    r = cliente.put(f"/api/v1/tareas/{tarea_id}/estado",
                    json={"estado": "en_progreso"}, headers=CABECERAS)
    assert r.status_code == 200
    assert r.json()["datos"]["estado"] == "en_progreso"


def test_transicion_de_estado_invalida(cliente):
    tarea_id = crear(cliente).json()["datos"]["tarea_id"]
    cliente.put(f"/api/v1/tareas/{tarea_id}/estado",
                json={"estado": "completada"}, headers=CABECERAS)
    r = cliente.put(f"/api/v1/tareas/{tarea_id}/estado",
                    json={"estado": "pendiente"}, headers=CABECERAS)
    assert r.status_code == 400


def test_estado_inexistente(cliente):
    tarea_id = crear(cliente).json()["datos"]["tarea_id"]
    r = cliente.put(f"/api/v1/tareas/{tarea_id}/estado",
                    json={"estado": "archivada"}, headers=CABECERAS)
    assert r.status_code == 400


def test_eliminacion_es_logica(cliente):
    tarea_id = crear(cliente).json()["datos"]["tarea_id"]
    r = cliente.delete(f"/api/v1/tareas/{tarea_id}", headers=CABECERAS)
    assert r.status_code == 200
    assert r.json()["datos"]["estado"] == "cancelada"
    # La tarea sigue existiendo: no se borró de la base de datos
    r2 = cliente.get(f"/api/v1/tareas/{tarea_id}", headers=CABECERAS)
    assert r2.status_code == 200
    assert r2.json()["datos"]["estado"] == "cancelada"


def test_header_request_id(cliente):
    r = cliente.get("/salud")
    assert r.headers.get("X-Request-Id")
