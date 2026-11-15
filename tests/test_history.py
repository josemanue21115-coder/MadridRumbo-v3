"""Tests aislados con SQLite; PostgreSQL real se valida por separado."""
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.db import normalize_database_url
from src.history import get_thread_messages, save_closed_turn


def test_normalize_render_url():
    assert normalize_database_url("postgres://host/db") == "postgresql://host/db"
    with pytest.raises(ValueError):
        normalize_database_url("")


def test_history_isolated_ordered_and_validated():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        save_closed_turn(session, "hilo-1", "Pregunta 1", "Respuesta 1")
        save_closed_turn(session, "hilo-2", "Pregunta 2", "Respuesta 2")
        save_closed_turn(session, "hilo-1", "Pregunta 3", "Respuesta 3")
        assert [(m.role, m.content) for m in get_thread_messages(session, "hilo-1")] == [
            ("user", "Pregunta 1"),
            ("assistant", "Respuesta 1"),
            ("user", "Pregunta 3"),
            ("assistant", "Respuesta 3"),
        ]
        assert len(get_thread_messages(session, "hilo-2")) == 2
        with pytest.raises(ValueError):
            save_closed_turn(session, "", "pregunta", "respuesta")
        with pytest.raises(ValueError):
            save_closed_turn(session, "hilo-1", "pregunta", "")
