"""Integración optativa SPEC-016; solo BD local desechable spec016 y usuario spec016."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

import config
import src.db as db
from app import app


def validar_destino_postgresql(raw):
    """Valida sin abrir conexiones; no admite parámetros que redirijan el destino."""
    url = make_url(db.normalize_database_url(raw))
    if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1"}
            or url.database != "spec016" or url.username != "spec016" or url.query):
        raise ValueError("Solo se admite PostgreSQL local, base y usuario spec016, sin parámetros adicionales")
    return url.set(drivername="postgresql+psycopg2")


@pytest.fixture
def api_postgresql(monkeypatch):
    raw = os.getenv("SPEC016_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("requiere SPEC016_TEST_DATABASE_URL de PostgreSQL local desechable")
    url = validar_destino_postgresql(raw)
    admin = create_engine(url)
    # Cada caso posee su esquema; no se eliminan tablas públicas ni datos ajenos.
    schema = "spec016_" + uuid4().hex
    motor = None
    creado = False
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        creado = True
        motor = create_engine(url.update_query_dict({"options": f"-csearch_path={schema}"}))
        monkeypatch.setattr(db, "get_engine", lambda: motor)
        monkeypatch.setenv(config.VARIABLE_MODO_SIMULADO, config.VALOR_MODO_SIMULADO)
        monkeypatch.setattr(config, "API_KEY", "clave-de-prueba")
        monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 10_000)
        with TestClient(app) as cliente:
            cliente.params = {"api_key": "clave-de-prueba"}
            yield cliente, motor
    finally:
        if motor is not None:
            motor.dispose()
        if creado:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.mark.parametrize("url", [
    "postgresql://spec016:prueba@example.org/spec016",
    "postgresql://spec016:prueba@localhost/produccion",
    "postgresql://postgres:prueba@localhost/spec016",
    "sqlite://",
    "postgresql://spec016:prueba@localhost/spec016?host=example.org",
])
def test_destinos_no_permitidos_no_se_conectan(url):
    with pytest.raises(ValueError):
        validar_destino_postgresql(url)


def test_postgresql_varios_turnos_y_hilos(api_postgresql):
    cliente, motor = api_postgresql
    for hilo, pregunta in [("uno", "Primera"), ("dos", "Ajena"), ("uno", "Segunda")]:
        assert cliente.post("/ask", json={"pregunta": pregunta, "thread_id": hilo}).status_code == 200
    respuesta = cliente.get("/threads/uno/messages")
    assert respuesta.status_code == 200
    mensajes = respuesta.json()
    assert [m["orden"] for m in mensajes] == [1, 2, 3, 4]
    assert [m["content"] for m in mensajes if m["role"] == "user"] == ["Primera", "Segunda"]
    assert len(cliente.get("/threads/dos/messages").json()) == 2


def test_postgresql_uuid_crea_y_recupera(api_postgresql):
    cliente, motor = api_postgresql
    respuesta = cliente.post("/ask", json={"pregunta": "Hola metro"})
    assert respuesta.status_code == 200
    hilo = respuesta.json()["thread_id"]
    assert len(cliente.get(f"/threads/{hilo}/messages").json()) == 2


@pytest.mark.parametrize("modo", ["manual", "automatico", "rechazo", "rechazo_parcial"])
def test_postgresql_cierre_por_decision(api_postgresql, modo):
    cliente, motor = api_postgresql
    pregunta = "Dos rutas de Sol a Atocha" if modo == "rechazo_parcial" else "Ruta de Sol a Atocha"
    final = cliente.post("/ask", json={"pregunta": pregunta, "thread_id": "decision", "auto_aprobar": modo == "automatico"})
    assert final.status_code == 200
    if modo != "automatico":
        assert cliente.get("/threads/decision/messages").json() == []
        if modo == "rechazo_parcial":
            parcial = cliente.post("/approve", json={"thread_id": "decision", "aprobado": False, "plan_id": "ruta-1"})
            assert parcial.json()["pendiente_hitl"] is True
            assert cliente.get("/threads/decision/messages").json() == []
        final = cliente.post("/approve", json={"thread_id": "decision", "aprobado": modo == "manual"})
    assert final.status_code == 200
    assert final.json()["done"] is (modo in {"manual", "automatico"})
    mensajes = cliente.get("/threads/decision/messages").json()
    assert [m["content"] for m in mensajes] == [pregunta, final.json()["respuesta"]]
    repetida = cliente.post("/approve", json={"thread_id": "decision", "aprobado": True})
    assert repetida.json()["error"]
    assert cliente.get("/threads/decision/messages").json() == mensajes


@pytest.mark.parametrize("existente", [False, True])
def test_rollback_postgresql(api_postgresql, monkeypatch, existente):
    from sqlmodel import Session, select
    from src.api import servicio
    from src.models import Conversation, Message

    cliente, motor = api_postgresql
    if existente:
        assert cliente.post("/ask", json={"pregunta": "Anterior", "thread_id": "atomicidad"}).status_code == 200
    with motor.begin() as connection:
        connection.execute(text("ALTER TABLE messages ADD CONSTRAINT rechazo_spec016 CHECK (content <> 'SPEC016_RECHAZAR')"))
    agente = servicio.obtener_agente()
    llamadas = []
    def responder(*args):
        llamadas.append(True)
        return {"respuesta": "SPEC016_RECHAZAR", "done": True, "hitl_pendiente": False,
                "plan": [], "log": [], "traza": []}
    monkeypatch.setattr(agente, "procesar_turno", responder)
    respuesta = cliente.post("/ask", json={"pregunta": "Pregunta fallida", "thread_id": "atomicidad"})
    assert respuesta.status_code == 500
    assert llamadas == [True]
    with Session(motor) as sesion:
        assert len(sesion.exec(select(Conversation)).all()) == int(existente)
        assert len(sesion.exec(select(Message)).all()) == 2 * int(existente)


def test_historial_tras_reinicio_api(api_postgresql):
    import subprocess
    import sys

    cliente, motor = api_postgresql
    entorno = os.environ.copy()
    entorno["DATABASE_URL"] = motor.url.render_as_string(hide_password=False)
    entorno["PYTHON_DOTENV_DISABLED"] = "1"
    entorno["API_KEY"] = "clave-de-prueba"
    entorno[config.VARIABLE_MODO_SIMULADO] = config.VALOR_MODO_SIMULADO
    guardar = """
from fastapi.testclient import TestClient
from app import app
with TestClient(app) as cliente:
    cliente.params = {'api_key': 'clave-de-prueba'}
    assert cliente.post('/ask', json={'pregunta': 'Guardar entre procesos', 'thread_id': 'reinicio'}).status_code == 200
    assert cliente.post('/ask', json={'pregunta': 'Ruta de Sol a Atocha', 'thread_id': 'solo-temporal', 'auto_aprobar': False}).json()['pendiente_hitl']
    assert cliente.get('/threads/solo-temporal/messages').json() == []
print('guardado')
"""
    recuperar = """
from fastapi.testclient import TestClient
from app import app
with TestClient(app) as cliente:
    cliente.params = {'api_key': 'clave-de-prueba'}
    respuesta = cliente.get('/threads/reinicio/messages')
    assert respuesta.status_code == 200
    assert [m['orden'] for m in respuesta.json()] == [1, 2]
    assert respuesta.json()[0]['content'] == 'Guardar entre procesos'
    assert cliente.get('/threads/solo-temporal/messages').status_code == 404
print('recuperado')
"""
    for codigo, esperado in [(guardar, "guardado"), (recuperar, "recuperado")]:
        proceso = subprocess.run([sys.executable, "-c", codigo], env=entorno, capture_output=True,
                                 text=True, timeout=30)
        assert proceso.returncode == 0, proceso.stderr
        assert esperado in proceso.stdout
