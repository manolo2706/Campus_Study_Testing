"""Conexión a MySQL con SQLAlchemy."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import config

opciones = {"pool_pre_ping": True}
if config.base_datos_url.startswith("sqlite"):
    # Solo se usa en las pruebas automáticas.
    opciones = {"connect_args": {"check_same_thread": False}}

motor = create_engine(config.base_datos_url, **opciones)
Sesion = sessionmaker(bind=motor, autoflush=False, autocommit=False)
Base = declarative_base()


def obtener_bd():
    bd = Sesion()
    try:
        yield bd
    finally:
        bd.close()
