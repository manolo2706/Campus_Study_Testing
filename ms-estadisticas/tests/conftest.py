import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "secret-pruebas-campusstudy-valido"

from datetime import datetime

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services import tiempo

# Una sola conexión en memoria: si no, cada request vería una base vacía.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
database.engine = engine
database.SessionLocal = SessionLocal

# Fecha fija para que las pruebas no dependan del día en que se corren.
AHORA_PRUEBAS = datetime(2026, 10, 12, 10, 0, tzinfo=tiempo.ZONA_COLOMBIA)


class Reloj:
    def __init__(self, momento: datetime) -> None:
        self.momento = momento

    def __call__(self) -> datetime:
        return self.momento


def token_para(usuario_id: int = 25, nombre: str = "Ana") -> str:
    return jwt.encode(
        {"sub": str(usuario_id), "nombre": nombre},
        settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture(autouse=True)
def reloj(monkeypatch):
    """Congela tiempo.ahora(). Para mover el reloj: reloj.momento = datetime(..., tzinfo=ZONA_COLOMBIA)."""
    fijo = Reloj(AHORA_PRUEBAS)
    monkeypatch.setattr(tiempo, "_reloj", fijo)
    return fijo


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token_para()}"
        yield test_client
    app.dependency_overrides.clear()
