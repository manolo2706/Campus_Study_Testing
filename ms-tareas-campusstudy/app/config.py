"""Configuración del microservicio. Todo se puede cambiar desde el archivo .env.

Para la integración (tercera entrega) lo importante es que las URLs y las RUTAS de
los otros servicios son configurables. Si un equipo publica su endpoint con otra
ruta, se ajusta aquí y no hay que tocar el código.
"""
import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # --- Identificación del servicio ---
    nombre_servicio: str = "ms-tareas"
    version_api: str = "v1"
    version_contrato: str = "1.0"
    zona_horaria: str = "America/Bogota"  # UTC-5, acordado en el contrato

    # --- Base de datos MySQL ---
    base_datos_url: str = (
        "mysql+pymysql://root:root@localhost:3306/campusstudy_tareas?charset=utf8mb4"
    )

    # --- URLs de los servicios de los otros equipos ---
    url_usuarios: str = "http://localhost:8008"
    url_materias: str = "http://localhost:8009"
    url_grupos: str = "http://localhost:8002"
    url_notificaciones: str = "http://localhost:8007"

    # --- Rutas de cada servicio (se ajustan a lo que publique cada equipo) ---
    ruta_usuario: str = "/api/v1/usuarios/{id}"
    ruta_materia: str = "/api/v1/materias/{id}"
    ruta_grupo: str = "/api/v1/grupos/{id}"
    ruta_notificacion: str = "/api/v1/notificaciones"
    ruta_validar_token: str = "/api/v1/auth/validar"

    # --- Modo simulado ---
    # true  -> no se llama por red, se responden datos de prueba (primera entrega)
    # false -> se llama de verdad a los servicios de los otros equipos (integración)
    simular_servicios: bool = False
    simular_notificaciones_caidas: bool = False

    # --- Seguridad ---
    # Si el acuerdo de integración es que cada servicio valide el token contra
    # Usuarios, se pone en true. Si lo valida el API Gateway, se deja en false.
    validar_token_con_usuarios: bool = False
    # Token propio para las llamadas entre servicios, si los equipos lo acuerdan.
    token_servicio: str = ""
    # Reenviar el token del estudiante en las llamadas salientes.
    propagar_token_usuario: bool = True
    # Orígenes permitidos para el Front (#6). Varios se separan con coma.
    origenes_permitidos: str = "*"

    # --- Rendimiento de la integración ---
    # Evita preguntar lo mismo muchas veces seguidas a Usuarios y Materias.
    cache_segundos_referencias: int = 60
    cache_segundos_token: int = 120
    # Horas que se conserva una clave de idempotencia para no duplicar tareas.
    horas_idempotencia: int = 24

    # --- Manejo de fallos (sección J del contrato) ---
    timeout_segundos: float = 3.0
    esperas_reintento: str = "1,2"       # segundos entre reintentos
    fallos_para_abrir_circuito: int = 5
    segundos_circuito_abierto: int = 30
    minutos_reintento_eventos: int = 5
    horas_maximo_evento: int = 24

    # --- Compatibilidad con Notificaciones (#7) ---
    # Si el equipo de Notificaciones usa otros nombres de campo, se renombran aquí
    # sin tocar el código. Ejemplo: {"usuario_id": "destinatario", "tipo": "evento"}
    notificacion_mapa_campos: str = "{}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def esperas(self) -> list[float]:
        return [float(x) for x in self.esperas_reintento.split(",") if x.strip()]

    @property
    def origenes(self) -> list[str]:
        return [o.strip() for o in self.origenes_permitidos.split(",") if o.strip()]

    @property
    def mapa_notificacion(self) -> dict:
        try:
            valor = json.loads(self.notificacion_mapa_campos or "{}")
            return valor if isinstance(valor, dict) else {}
        except json.JSONDecodeError:
            return {}


config = Config()
