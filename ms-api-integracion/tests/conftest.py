import os
import sys
from pathlib import Path

os.environ.setdefault("STUBS_ENABLED", "true")
os.environ.setdefault("JWT_SECRET", "9a8f7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a")

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def token(client: TestClient) -> str:
    respuesta = client.post(
        "/api/v1/auth/login",
        json={"correo": "estudiante@univer.edu.co", "password": "secreto123"},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["data"]["token"]


@pytest.fixture(scope="session")
def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
