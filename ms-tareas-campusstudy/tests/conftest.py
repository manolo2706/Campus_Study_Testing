"""Las pruebas usan SQLite en memoria para no depender de MySQL."""
import os
import tempfile

os.environ["BASE_DATOS_URL"] = f"sqlite:///{tempfile.gettempdir()}/pruebas_tareas.db"
os.environ["SIMULAR_SERVICIOS"] = "true"
os.environ["ESPERAS_REINTENTO"] = "0.01,0.01"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, motor
from app.main import app

CABECERAS = {"Authorization": "Bearer token-de-prueba"}


@pytest.fixture()
def cliente():
    Base.metadata.drop_all(bind=motor)
    Base.metadata.create_all(bind=motor)
    with TestClient(app) as c:
        yield c
