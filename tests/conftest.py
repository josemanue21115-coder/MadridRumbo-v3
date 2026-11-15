"""Configuración común de los tests: ninguno puede hacer una petición HTTP real."""
import urllib.request
from contextlib import contextmanager

import pytest


@pytest.fixture(autouse=True)
def sin_peticiones_reales(monkeypatch):
    # Red de seguridad: si algún test llega a urlopen sin su propio doble, falla en vez de salir a internet.
    def bloqueado(*args, **kwargs):
        raise AssertionError("petición HTTP real en un test: usa un doble de prueba")

    monkeypatch.setattr(urllib.request, "urlopen", bloqueado)


@pytest.fixture
def motor_api():
    """Una SQLite nueva por caso, compartida por sus sesiones y el TestClient."""
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, create_engine

    from src import models  # registra las tablas antes de preparar la base

    motor = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        SQLModel.metadata.create_all(motor)
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def sesiones_api(motor_api):
    """Abre una sesión independiente y la cierra aunque el test falle."""
    from sqlmodel import Session

    @contextmanager
    def abrir_sesion():
        with Session(motor_api) as sesion:
            yield sesion

    return abrir_sesion


@pytest.fixture
def entorno_api(monkeypatch, motor_api, sesiones_api):
    """Sustituye solo para tests API el agente, los planes y el acceso a datos."""
    from sqlmodel import SQLModel

    import config
    import src.db as db
    from app import app
    from src.api import servicio

    monkeypatch.setenv(config.VARIABLE_MODO_SIMULADO, config.VALOR_MODO_SIMULADO)
    monkeypatch.setattr(servicio, "_agente", None)
    monkeypatch.setattr(servicio, "_planes_pendientes", {})
    monkeypatch.setattr(db, "get_engine", lambda: motor_api)
    # Doble explícito para el futuro lifespan; no se conecta a PostgreSQL.
    monkeypatch.setattr(db, "create_db_and_tables", lambda: SQLModel.metadata.create_all(motor_api))

    def sesion_por_peticion():
        with sesiones_api() as sesion:
            yield sesion

    # Se conserva cualquier override previo y monkeypatch restaura el original.
    monkeypatch.setattr(
        app,
        "dependency_overrides",
        {**app.dependency_overrides, db.get_session: sesion_por_peticion},
    )


@pytest.fixture
def cliente_api(entorno_api):
    """Cliente por caso que ejecuta startup/shutdown mediante su contexto."""
    from fastapi.testclient import TestClient

    from app import app

    with TestClient(app) as cliente:
        yield cliente
