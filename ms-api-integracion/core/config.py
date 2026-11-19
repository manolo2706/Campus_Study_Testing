from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CampusStudy - API Gateway"
    api_version: str = "1.0.0"

    auth_url: str = "http://localhost:8081"
    grupos_url: str = "http://localhost:8082"
    notificaciones_url: str = "http://localhost:3000"
    estadisticas_url: str = "http://localhost:8000"
    materias_url: str = "http://localhost:8083"
    tareas_url: str = "http://localhost:8085"

    grupos_auth_mode: str = "jwt"
    servicio_token: str = ""

    jwt_secret: str = "9a8f7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a"
    jwt_algorithms: str = "HS256"

    request_timeout: float = 5.0
    connect_timeout: float = 2.0
    max_retries: int = 2
    retry_base_delay: float = 0.5
    retry_max_delay: float = 2.0

    circuit_fail_threshold: int = 3
    circuit_recovery_seconds: float = 30.0

    cache_ttl_seconds: float = 60.0

    cors_origins: str = "*"
    stubs_enabled: bool = False

    @property
    def jwt_algorithm_list(self) -> list[str]:
        return [a.strip() for a in self.jwt_algorithms.split(",") if a.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
