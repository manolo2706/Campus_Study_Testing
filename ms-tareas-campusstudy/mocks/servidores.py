"""Simuladores de los microservicios de los otros equipos.

Sirven para probar la INTEGRACIÓN REAL por HTTP antes de que todos los servicios
estén desplegados: nuestro servicio hace peticiones de red de verdad, con sus
reintentos y su manejo de errores, solo que del otro lado responde este programa.

Se levantan los cuatro de una vez:

    python mocks/servidores.py

Cada simulador expone además dos endpoints para la demostración:
    POST /mock/caer      -> deja de responder (simula el servicio caído)
    POST /mock/levantar  -> vuelve a responder

A propósito, cada simulador responde con una estructura distinta:
  - Usuarios y Notificaciones usan la estructura exacta del contrato
  - Materias devuelve los campos planos y en inglés ("id", "name")
  - Grupos envuelve en "data" y llama "miembros" a los integrantes

Es para comprobar que los adaptadores de app/adaptadores.py hacen su trabajo y
que nuestro servicio no se rompe si un equipo usa otros nombres de campo.
"""
import asyncio
import sys
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

PUERTOS = {"usuarios": 8008, "materias": 8009, "grupos": 8002, "notificaciones": 8007}

# Datos de prueba. 999999 no existe en ningún servicio; 888888 existe pero inactivo.
INTEGRANTES = {1: [1, 2, 3, 692464], 2: [10, 11], 3: [692464, 897847, 729495]}
MATERIAS = {12: "Sistemas Distribuidos", 13: "Bases de Datos", 14: "Ingeniería de Software"}

estado = {nombre: True for nombre in PUERTOS}   # True = el servicio responde
recibidas = {nombre: [] for nombre in PUERTOS}  # historial, para revisar en la demo


def base(nombre: str) -> FastAPI:
    app = FastAPI(title=f"Simulador de {nombre}", version="mock")

    @app.middleware("http")
    async def caido(request, call_next):
        if not estado[nombre] and not request.url.path.startswith("/mock"):
            # No responde nada útil: se simula un servicio fuera de servicio.
            await asyncio.sleep(5)
            return JSONResponse(status_code=503, content={"error": "fuera de servicio"})
        return await call_next(request)

    @app.get("/salud")
    def salud():
        return {"servicio": nombre, "estado": "arriba" if estado[nombre] else "caido"}

    @app.post("/mock/caer")
    def caer():
        estado[nombre] = False
        return {"servicio": nombre, "estado": "caido"}

    @app.post("/mock/levantar")
    def levantar():
        estado[nombre] = True
        return {"servicio": nombre, "estado": "arriba"}

    @app.get("/mock/recibidas")
    def ver_recibidas():
        return {"servicio": nombre, "peticiones": recibidas[nombre]}

    return app


# --- Usuarios (#8): estructura exacta del contrato ---
usuarios = base("usuarios")


@usuarios.get("/api/v1/usuarios/{usuario_id}")
def obtener_usuario(usuario_id: int):
    recibidas["usuarios"].append(usuario_id)
    if usuario_id == 999999:
        return JSONResponse(status_code=404, content={"exito": False,
                            "error": {"codigo": 404, "mensaje": "El usuario no existe"}})
    return {
        "exito": True,
        "datos": {
            "usuario_id": usuario_id,
            "nombre": f"Estudiante {usuario_id}",
            "activo": usuario_id != 888888,
        },
        "mensaje": "Consulta realizada correctamente",
    }


@usuarios.get("/api/v1/auth/validar")
def validar_token():
    return {"exito": True, "datos": {"valido": True}, "mensaje": "Token válido"}


# --- Materias (#9): campos planos y en inglés, a propósito ---
materias = base("materias")


@materias.get("/api/v1/materias/{materia_id}")
def obtener_materia(materia_id: int):
    recibidas["materias"].append(materia_id)
    if materia_id == 999999 or materia_id not in MATERIAS:
        return JSONResponse(status_code=404, content={"message": "Subject not found"})
    return {"id": materia_id, "name": MATERIAS[materia_id], "credits": 3}


# --- Grupos (#2): envuelto en "data" y con "miembros" como lista de objetos ---
grupos = base("grupos")


@grupos.get("/api/v1/grupos/{grupo_id}")
def obtener_grupo(grupo_id: int):
    recibidas["grupos"].append(grupo_id)
    if grupo_id == 999999 or grupo_id not in INTEGRANTES:
        return JSONResponse(status_code=404, content={"data": None, "message": "no existe"})
    return {
        "data": {
            "grupo_id": grupo_id,
            "nombre": f"Grupo de estudio {grupo_id}",
            "miembros": [{"usuario_id": u} for u in INTEGRANTES[grupo_id]],
        }
    }


# --- Notificaciones (#7): estructura del contrato ---
notificaciones = base("notificaciones")
contador = {"n": 0}


@notificaciones.post("/api/v1/notificaciones", status_code=201)
def crear_notificacion(evento: dict):
    contador["n"] += 1
    recibidas["notificaciones"].append(evento)
    print(f"  [notificaciones] evento recibido: {evento.get('tipo')} "
          f"para el usuario {evento.get('usuario_id')}")
    return {"exito": True, "datos": {"notificacion_id": contador["n"]},
            "mensaje": "Notificación registrada"}


APPS = {"usuarios": usuarios, "materias": materias,
        "grupos": grupos, "notificaciones": notificaciones}


def arrancar(nombre: str, puerto: int):
    uvicorn.run(APPS[nombre], host="127.0.0.1", port=puerto, log_level="warning")


def main():
    print("Simuladores de los microservicios de CampusStudy")
    print("-" * 52)
    for nombre, puerto in PUERTOS.items():
        hilo = threading.Thread(target=arrancar, args=(nombre, puerto), daemon=True)
        hilo.start()
        print(f"  {nombre:<16} http://localhost:{puerto}")
    print("-" * 52)
    print("Para simular una caída:  curl -X POST http://localhost:8008/mock/caer")
    print("Para restablecerlo:      curl -X POST http://localhost:8008/mock/levantar")
    print("Detener todo con Ctrl+C")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nSimuladores detenidos")
        sys.exit(0)


if __name__ == "__main__":
    main()
