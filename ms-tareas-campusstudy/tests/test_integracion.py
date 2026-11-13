"""Pruebas de integración real por HTTP contra los simuladores de los otros equipos.

A diferencia de test_contrato.py, aquí NO se usa el modo simulado interno: el
servicio levanta peticiones de red de verdad contra los servidores de mocks/,
pasando por los reintentos, los adaptadores y el manejo de errores.

Estas mismas pruebas sirven el día de la integración: basta con apuntar las URLs
a los servicios reales de cada equipo en lugar de a los simuladores.
"""
import threading
import time
from datetime import timedelta

import pytest
import uvicorn

from app import clientes
from app.config import config
from app.utilidades import hoy
from mocks import servidores
from tests.conftest import CABECERAS

# Puertos propios de las pruebas, para no chocar con los simuladores en ejecución
PUERTOS = {"usuarios": 8808, "materias": 8809, "grupos": 8802, "notificaciones": 8807}
ENTREGA = (hoy() + timedelta(days=30)).strftime("%Y-%m-%d")


def _levantar(app, puerto):
    configuracion = uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="error")
    servidor = uvicorn.Server(configuracion)
    threading.Thread(target=servidor.run, daemon=True).start()
    for _ in range(100):
        if servidor.started:
            return servidor
        time.sleep(0.05)
    raise RuntimeError(f"El simulador del puerto {puerto} no arrancó")


@pytest.fixture(scope="module", autouse=True)
def simuladores():
    """Levanta los cuatro simuladores y apunta el servicio hacia ellos."""
    servidores_activos = [_levantar(servidores.APPS[n], p) for n, p in PUERTOS.items()]

    config.simular_servicios = False
    config.timeout_segundos = 0.5          # las pruebas no deben tardar
    config.cache_segundos_referencias = 60
    for nombre, puerto in PUERTOS.items():
        getattr(clientes, nombre).url_base = f"http://127.0.0.1:{puerto}"

    yield

    for s in servidores_activos:
        s.should_exit = True
    config.simular_servicios = True


@pytest.fixture(autouse=True)
def estado_limpio():
    """Cada prueba empieza con los simuladores arriba y sin caché."""
    for nombre in PUERTOS:
        servidores.estado[nombre] = True
        servidores.recibidas[nombre].clear()
        getattr(clientes, nombre).circuito.registrar_exito()
    clientes.limpiar_caches()
    yield


def nueva_tarea(**extra):
    datos = {
        "titulo": "Tarea de integración",
        "usuario_id": 692464,
        "materia_id": 12,
        "grupo_id": 1,
        "fecha_entrega": ENTREGA,
        "prioridad": "alta",
    }
    datos.update(extra)
    return datos


def crear(cliente, cabeceras=None, **extra):
    return cliente.post("/api/v1/tareas", json=nueva_tarea(**extra),
                        headers={**CABECERAS, **(cabeceras or {})})


# --- Comunicación real con los tres proveedores ---
def test_crear_tarea_consultando_los_servicios_reales(cliente):
    r = crear(cliente)
    assert r.status_code == 201, r.text
    assert r.json()["datos"]["estado"] == "pendiente"
    # Se comprueba que realmente se llamó a cada servicio por HTTP
    assert 692464 in servidores.recibidas["usuarios"]
    assert 12 in servidores.recibidas["materias"]
    assert 1 in servidores.recibidas["grupos"]


def test_el_evento_llega_a_notificaciones(cliente):
    r = crear(cliente)
    assert r.status_code == 201
    eventos = servidores.recibidas["notificaciones"]
    assert eventos, "Notificaciones no recibió ningún evento"
    assert eventos[0]["tipo"] == "tarea_creada"
    assert "referencia_id" in eventos[0]


def test_tarea_de_grupo_notifica_a_cada_integrante(cliente):
    # El grupo 3 del simulador tiene tres integrantes
    r = crear(cliente, usuario_id=692464, grupo_id=3)
    assert r.status_code == 201
    assert len(servidores.recibidas["notificaciones"]) == 3


# --- Los adaptadores frente a estructuras distintas ---
def test_adaptador_materias_campos_planos_en_ingles(cliente):
    """El simulador de Materias responde {"id":..., "name":...} y aun así funciona."""
    r = crear(cliente, materia_id=13)
    assert r.status_code == 201


def test_adaptador_grupos_envuelto_en_data_con_miembros(cliente):
    """El simulador de Grupos envuelve en "data" y usa "miembros" en vez de integrantes."""
    r = crear(cliente, grupo_id=1, usuario_id=692464)
    assert r.status_code == 201


def test_usuario_que_no_pertenece_al_grupo(cliente):
    r = crear(cliente, usuario_id=55, grupo_id=1)
    assert r.status_code == 400
    assert "integrante" in r.json()["error"]["mensaje"].lower()


# --- El proveedor responde 404: es un error de datos, no una falla ---
def test_usuario_inexistente_devuelve_400(cliente):
    r = crear(cliente, usuario_id=999999, grupo_id=None)
    assert r.status_code == 400


def test_materia_inexistente_devuelve_400(cliente):
    r = crear(cliente, materia_id=999999)
    assert r.status_code == 400


def test_usuario_inactivo_devuelve_400(cliente):
    r = crear(cliente, usuario_id=888888, grupo_id=None)
    assert r.status_code == 400
    assert "activo" in r.json()["error"]["mensaje"].lower()


# --- El proveedor no responde: 503 y la tarea no se crea ---
def test_proveedor_caido_devuelve_503(cliente):
    servidores.estado["usuarios"] = False
    r = crear(cliente)
    assert r.status_code == 503
    assert r.json()["error"]["tipo"] == "SERVICIO_NO_DISPONIBLE"
    # Y lo más importante: no quedó ninguna tarea a medias
    listado = cliente.get("/api/v1/tareas?usuario_id=692464", headers=CABECERAS)
    assert listado.json()["datos"]["total"] == 0


def test_notificaciones_caido_no_impide_crear(cliente):
    from app.database import Sesion
    from app.models import EventoPendiente

    servidores.estado["notificaciones"] = False
    r = crear(cliente)
    assert r.status_code == 201, "La caída de Notificaciones no debe bloquear la tarea"

    bd = Sesion()
    assert bd.query(EventoPendiente).count() > 0
    bd.close()


def test_consultas_funcionan_con_todos_los_servicios_caidos(cliente):
    r = crear(cliente)
    tarea_id = r.json()["datos"]["tarea_id"]
    for nombre in PUERTOS:
        servidores.estado[nombre] = False

    assert cliente.get(f"/api/v1/tareas/{tarea_id}", headers=CABECERAS).status_code == 200
    assert cliente.get("/api/v1/tareas?usuario_id=692464", headers=CABECERAS).status_code == 200
    assert cliente.get("/api/v1/tareas/resumen?usuario_id=692464",
                       headers=CABECERAS).status_code == 200


# --- Idempotencia ---
def test_misma_clave_no_crea_dos_tareas(cliente):
    cabeceras = {"X-Idempotency-Key": "clave-de-prueba-001"}
    primera = crear(cliente, cabeceras=cabeceras)
    segunda = crear(cliente, cabeceras=cabeceras)

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert primera.json()["datos"]["tarea_id"] == segunda.json()["datos"]["tarea_id"]

    listado = cliente.get("/api/v1/tareas?usuario_id=692464", headers=CABECERAS)
    assert listado.json()["datos"]["total"] == 1


def test_sin_clave_de_idempotencia_si_se_crean_dos(cliente):
    crear(cliente)
    crear(cliente)
    listado = cliente.get("/api/v1/tareas?usuario_id=692464", headers=CABECERAS)
    assert listado.json()["datos"]["total"] == 2


# --- Trazabilidad entre servicios ---
def test_el_request_id_se_conserva(cliente):
    r = cliente.get("/salud", headers={**CABECERAS, "X-Request-Id": "trace-123"})
    assert r.headers["X-Request-Id"] == "trace-123"


def test_estado_de_dependencias(cliente):
    r = cliente.get("/salud/dependencias")
    assert r.status_code == 200
    assert r.json()["datos"]["dependencias"]["usuarios"] == "disponible"

    servidores.estado["grupos"] = False
    r2 = cliente.get("/salud/dependencias")
    assert r2.json()["datos"]["dependencias"]["grupos"] == "sin respuesta"


# --- El caché evita preguntar lo mismo muchas veces ---
def test_el_cache_evita_consultas_repetidas(cliente):
    crear(cliente)
    crear(cliente)
    crear(cliente)
    assert servidores.recibidas["usuarios"].count(692464) == 1
