"""Validación SPEC-014 sin LLM; PostgreSQL requiere una BD temporal explícita."""
import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

import config
import src.db as db
from src.history import get_thread_messages, save_closed_turn
from src.models import Conversation, Message


@pytest.fixture(params=["sqlite", "postgresql"])
def engine(request, monkeypatch):
    """Solo se crean/borran tablas en memoria o en una BD dedicada de pruebas."""
    if request.param == "postgresql":
        url = os.getenv("SPEC014_TEST_DATABASE_URL")
        if not url:
            pytest.skip("requiere SPEC014_TEST_DATABASE_URL de una BD temporal")
        parsed = make_url(url)
        if parsed.host not in {"localhost", "127.0.0.1"} or parsed.database != "spec014":
            pytest.fail("la integración solo admite localhost y la BD temporal spec014")
        monkeypatch.setattr(config, "DATABASE_URL", url)
        db.get_engine.cache_clear()
        result = db.get_engine()
        db.create_db_and_tables()
    else:
        result = create_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(result)
    try:
        yield result
    finally:
        SQLModel.metadata.drop_all(result)
        result.dispose()
        db.get_engine.cache_clear()


def test_tablas_modelos_y_persistencia_entre_sesiones(engine):
    assert {"conversations", "messages"} <= set(inspect(engine).get_table_names())
    with Session(engine) as session:
        save_closed_turn(session, "uno", "Pregunta 1", "Respuesta 1")
        save_closed_turn(session, "dos", "Otra pregunta", "Otra respuesta")
        save_closed_turn(session, "uno", "Pregunta 2", "Respuesta 2")
    with Session(engine) as nueva:
        messages = get_thread_messages(nueva, "uno")
        assert [(m.role, m.content) for m in messages] == [
            ("user", "Pregunta 1"), ("assistant", "Respuesta 1"),
            ("user", "Pregunta 2"), ("assistant", "Respuesta 2"),
        ]
        assert [m.id for m in messages] == sorted(m.id for m in messages)
        assert all(m.created_at is not None and m.thread_id == "uno" for m in messages)
        assert nueva.get(Conversation, "uno").created_at is not None
        assert len(get_thread_messages(nueva, "dos")) == 2
        assert get_thread_messages(nueva, "inexistente") == []


@pytest.mark.parametrize("field", ["thread_id", "question", "answer"])
@pytest.mark.parametrize("invalid", ["", "   ", None, 42])
def test_rechaza_entradas_invalidas_sin_escrituras(engine, field, invalid):
    args = dict(thread_id="validacion", question="Pregunta", answer="Respuesta")
    args[field] = invalid
    with Session(engine) as session:
        with pytest.raises(ValueError):
            save_closed_turn(session, **args)
        assert session.exec(select(Conversation)).all() == []
        assert session.exec(select(Message)).all() == []


def test_limite_identificador(engine):
    with Session(engine) as session:
        save_closed_turn(session, "x" * 128, "Pregunta", "Respuesta")
        with pytest.raises(ValueError):
            save_closed_turn(session, "x" * 129, "Pregunta", "Respuesta")
        assert len(session.exec(select(Conversation)).all()) == 1


def test_persistencia_desde_otro_proceso(engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("SQLite en memoria no se comparte entre procesos")
    with Session(engine) as session:
        save_closed_turn(session, "otro-proceso", "Persistir", "Recuperar")
    env = os.environ.copy()
    env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    code = (
        "from src.db import get_session; "
        "from src.history import get_thread_messages; "
        "sessions = get_session(); session = next(sessions); "
        "assert [m.content for m in get_thread_messages(session, 'otro-proceso')] "
        "== ['Persistir', 'Recuperar']; sessions.close(); print('persistencia OK')"
    )
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "persistencia OK"


@pytest.mark.parametrize("existente", [False, True])
def test_rollback_del_segundo_mensaje_y_reutilizacion_sesion(engine, existente):
    """Falla la respuesta después de insertar la pregunta; se revierte el turno."""
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("ALTER TABLE messages ADD CONSTRAINT spec014_rechazo CHECK (content <> 'SPEC014_RECHAZAR')"))
        else:
            connection.execute(text("CREATE TRIGGER spec014_rechazo BEFORE INSERT ON messages WHEN NEW.content = 'SPEC014_RECHAZAR' BEGIN SELECT RAISE(ABORT, 'rechazo de prueba'); END"))
    with Session(engine) as session:
        if existente:
            save_closed_turn(session, "atomicidad", "Anterior", "Conservada")
        with pytest.raises(IntegrityError):
            save_closed_turn(session, "atomicidad", "Pregunta fallida", "SPEC014_RECHAZAR")
        assert len(session.exec(select(Conversation)).all()) == int(existente)
        assert [m.content for m in get_thread_messages(session, "atomicidad")] == (["Anterior", "Conservada"] if existente else [])
        save_closed_turn(session, "atomicidad", "Reintento", "Correcto")
    with Session(engine) as nueva:
        assert [m.content for m in get_thread_messages(nueva, "atomicidad")][-2:] == ["Reintento", "Correcto"]


@pytest.mark.parametrize("url,expected", [
    ("postgres://host/spec014", "postgresql+psycopg2://host/spec014"),
    ("postgresql://host/spec014", "postgresql+psycopg2://host/spec014"),
    ("postgresql+psycopg2://host/spec014", "postgresql+psycopg2://host/spec014"),
    ("postgresql+psycopg://host/spec014", "postgresql+psycopg://host/spec014"),
])
def test_engine_selecciona_driver_declarado(monkeypatch, url, expected):
    """El driver de requirements no depende del valor por defecto de SQLAlchemy."""
    monkeypatch.setattr(config, "DATABASE_URL", url)
    monkeypatch.setattr(db, "create_engine", lambda actual, **kwargs: actual)
    db.get_engine.cache_clear()
    try:
        assert db.get_engine() == expected
    finally:
        db.get_engine.cache_clear()


@pytest.mark.parametrize("url", [None, "", "   ", 42])
def test_url_vacia_o_no_textual(url):
    with pytest.raises(ValueError):
        db.normalize_database_url(url)


def test_engine_rechaza_sqlite_en_produccion(monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", "sqlite://")
    db.get_engine.cache_clear()
    try:
        with pytest.raises(ValueError):
            db.get_engine()
    finally:
        db.get_engine.cache_clear()
