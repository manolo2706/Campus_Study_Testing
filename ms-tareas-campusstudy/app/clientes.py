"""Comunicación con los microservicios de los otros equipos.

Implementa el manejo de fallos de la sección J del contrato:
  - tiempo de espera de 3 segundos por llamada
  - 2 reintentos con esperas de 1 y 2 segundos
  - circuit breaker: tras 5 fallos seguidos se pausan las llamadas 30 segundos
  - "sin respuesta" nunca se interpreta como "el dato no existe"

Y lo que agrega la integración:
  - las rutas de cada servicio se leen del archivo .env
  - se reenvía el token del estudiante y el X-Request-Id a cada llamada
  - las respuestas pasan por los adaptadores, así que no importa si otro equipo
    usa nombres de campo distintos
  - un caché corto evita preguntar lo mismo varias veces seguidas
"""
import asyncio
import logging
from datetime import timedelta

import httpx

from app import adaptadores, contexto
from app.config import config
from app.errores import ServicioNoDisponible
from app.utilidades import ahora

log = logging.getLogger("ms-tareas.clientes")


# ---------------------------------------------------------------------------
# Caché en memoria con vencimiento
# ---------------------------------------------------------------------------
class Cache:
    def __init__(self, segundos: int):
        self.segundos = segundos
        self._datos: dict = {}

    def obtener(self, clave):
        if self.segundos <= 0:
            return None
        registro = self._datos.get(clave)
        if not registro:
            return None
        valor, vence = registro
        if ahora() >= vence:
            self._datos.pop(clave, None)
            return None
        return valor

    def guardar(self, clave, valor):
        if self.segundos > 0:
            self._datos[clave] = (valor, ahora() + timedelta(seconds=self.segundos))

    def limpiar(self):
        self._datos.clear()


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------
class Circuito:
    def __init__(self):
        self.fallos = 0
        self.abierto_hasta = None

    def abierto(self) -> bool:
        return bool(self.abierto_hasta and ahora() < self.abierto_hasta)

    def registrar_fallo(self):
        self.fallos += 1
        if self.fallos >= config.fallos_para_abrir_circuito:
            self.abierto_hasta = ahora() + timedelta(seconds=config.segundos_circuito_abierto)
            self.fallos = 0
            log.error("Circuito abierto por %s segundos", config.segundos_circuito_abierto)

    def registrar_exito(self):
        self.fallos = 0
        self.abierto_hasta = None


# ---------------------------------------------------------------------------
# Cliente HTTP
# ---------------------------------------------------------------------------
class ClienteServicio:
    """Devuelve None cuando el proveedor responde 404, y lanza 503 si no responde."""

    def __init__(self, nombre: str, url_base: str):
        self.nombre = nombre
        self.url_base = url_base.rstrip("/")
        self.circuito = Circuito()

    def _cabeceras(self) -> dict:
        cabeceras = {
            "Accept": "application/json",
            "X-Request-Id": contexto.request_id(),
            "X-Origen-Servicio": config.nombre_servicio,
        }
        token = contexto.token() if config.propagar_token_usuario else ""
        token = token or config.token_servicio
        if token:
            cabeceras["Authorization"] = f"Bearer {token}"
        return cabeceras

    async def _llamar(self, metodo: str, ruta: str, json: dict | None = None):
        if self.circuito.abierto():
            log.warning("Circuito abierto para %s, no se intenta la llamada", self.nombre)
            raise ServicioNoDisponible(
                f"El servicio de {self.nombre} no está disponible en este momento"
            )

        url = f"{self.url_base}{ruta}"
        esperas = [0.0] + config.esperas  # primer intento + reintentos
        ultimo_error = None

        for numero, espera in enumerate(esperas, start=1):
            if espera:
                await asyncio.sleep(espera)
            try:
                async with httpx.AsyncClient(timeout=config.timeout_segundos) as cliente:
                    r = await cliente.request(metodo, url, json=json, headers=self._cabeceras())

                if r.status_code == 404:
                    self.circuito.registrar_exito()
                    return None
                if r.status_code in (401, 403):
                    # El proveedor respondió: no es una falla de red.
                    self.circuito.registrar_exito()
                    log.warning("%s rechazó la petición con %s", self.nombre, r.status_code)
                    raise ServicioNoDisponible(
                        f"El servicio de {self.nombre} rechazó la petición "
                        f"(código {r.status_code}); revisar el token entre servicios"
                    )
                if r.status_code >= 500:
                    ultimo_error = f"respuesta {r.status_code}"
                    log.warning("%s respondió %s (intento %s)", self.nombre, r.status_code, numero)
                    continue

                self.circuito.registrar_exito()
                try:
                    return r.json()
                except ValueError:
                    log.error("%s no devolvió JSON válido", self.nombre)
                    raise ServicioNoDisponible(
                        f"El servicio de {self.nombre} devolvió una respuesta que no es JSON"
                    )
            except (httpx.TimeoutException, httpx.TransportError) as e:
                ultimo_error = str(e) or type(e).__name__
                log.warning("Sin respuesta de %s (intento %s): %s", self.nombre, numero, ultimo_error)

        self.circuito.registrar_fallo()
        log.error(
            "El servicio de %s no respondió. Último error: %s | request_id=%s",
            self.nombre, ultimo_error, contexto.request_id(),
        )
        raise ServicioNoDisponible(
            f"El servicio de {self.nombre} no está disponible en este momento"
        )

    async def obtener(self, ruta: str):
        return await self._llamar("GET", ruta)

    async def publicar(self, ruta: str, json: dict):
        return await self._llamar("POST", ruta, json)

    async def disponible(self) -> bool:
        """Comprobación rápida para el endpoint de salud, sin reintentos."""
        for ruta in ("/salud", "/health", "/actuator/health", "/"):
            try:
                async with httpx.AsyncClient(timeout=2.0) as cliente:
                    r = await cliente.get(f"{self.url_base}{ruta}")
                if r.status_code < 500:
                    return True
            except (httpx.TimeoutException, httpx.TransportError):
                continue
        return False


usuarios = ClienteServicio("usuarios", config.url_usuarios)
materias = ClienteServicio("materias", config.url_materias)
grupos = ClienteServicio("grupos", config.url_grupos)
notificaciones = ClienteServicio("notificaciones", config.url_notificaciones)

cache_usuarios = Cache(config.cache_segundos_referencias)
cache_materias = Cache(config.cache_segundos_referencias)
cache_grupos = Cache(config.cache_segundos_referencias)
cache_tokens = Cache(config.cache_segundos_token)


def limpiar_caches():
    for c in (cache_usuarios, cache_materias, cache_grupos, cache_tokens):
        c.limpiar()


# ---------------------------------------------------------------------------
# Datos simulados (solo mientras un servicio todavía no esté desplegado)
#   usuario_id / materia_id / grupo_id = 999999 -> no existe (404)
#   usuario_id = 888888                         -> existe pero inactivo
# ---------------------------------------------------------------------------
INTEGRANTES_SIMULADOS = [1, 2, 3, 692464]


async def consultar_usuario(usuario_id: int):
    if config.simular_servicios:
        if usuario_id == 999999:
            return None
        return {"usuario_id": usuario_id, "nombre": "Estudiante de prueba",
                "activo": usuario_id != 888888}

    en_cache = cache_usuarios.obtener(usuario_id)
    if en_cache is not None:
        return en_cache or None

    ruta = config.ruta_usuario.format(id=usuario_id)
    datos = adaptadores.normalizar_usuario(await usuarios.obtener(ruta), usuario_id)
    cache_usuarios.guardar(usuario_id, datos or {})
    return datos


async def consultar_materia(materia_id: int):
    if config.simular_servicios:
        if materia_id == 999999:
            return None
        return {"materia_id": materia_id, "nombre": "Sistemas Distribuidos"}

    en_cache = cache_materias.obtener(materia_id)
    if en_cache is not None:
        return en_cache or None

    ruta = config.ruta_materia.format(id=materia_id)
    datos = adaptadores.normalizar_materia(await materias.obtener(ruta), materia_id)
    cache_materias.guardar(materia_id, datos or {})
    return datos


async def consultar_grupo(grupo_id: int):
    if config.simular_servicios:
        if grupo_id == 999999:
            return None
        return {"grupo_id": grupo_id, "nombre": "Grupo de estudio",
                "integrantes": INTEGRANTES_SIMULADOS}

    en_cache = cache_grupos.obtener(grupo_id)
    if en_cache is not None:
        return en_cache or None

    ruta = config.ruta_grupo.format(id=grupo_id)
    datos = adaptadores.normalizar_grupo(await grupos.obtener(ruta), grupo_id)
    cache_grupos.guardar(grupo_id, datos or {})
    return datos


async def enviar_notificacion(evento: dict):
    if config.simular_servicios:
        if config.simular_notificaciones_caidas:
            raise ServicioNoDisponible("El servicio de notificaciones no está disponible")
        log.info("Notificación simulada: %s", evento)
        return {"notificacion_id": 0}

    cuerpo = adaptadores.renombrar_campos(evento, config.mapa_notificacion)
    return await notificaciones.publicar(config.ruta_notificacion, cuerpo)


async def validar_token_remoto(token: str) -> bool:
    """Pregunta a Usuarios si el token es válido. Solo se usa si así se acordó."""
    if config.simular_servicios:
        return True

    en_cache = cache_tokens.obtener(token)
    if en_cache is not None:
        return bool(en_cache)

    respuesta = await usuarios.obtener(config.ruta_validar_token)
    valido = respuesta is not None
    cache_tokens.guardar(token, valido)
    return valido


async def estado_dependencias() -> dict:
    """Estado de los cuatro servicios, para el endpoint /salud/dependencias."""
    if config.simular_servicios:
        return {nombre: "simulado" for nombre in
                ("usuarios", "materias", "grupos", "notificaciones")}

    nombres = ["usuarios", "materias", "grupos", "notificaciones"]
    clientes = [usuarios, materias, grupos, notificaciones]
    resultados = await asyncio.gather(*(c.disponible() for c in clientes))
    return {
        nombre: ("disponible" if ok else "sin respuesta")
        for nombre, ok in zip(nombres, resultados)
    }
