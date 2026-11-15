"""SPEC-016 T1: cada caso de API recibe agente, planes y base propios."""
import pytest
from sqlmodel import select

from src.api import historial, servicio
from src.history import get_thread_messages, save_closed_turn
from src.models import Conversation, Message


@pytest.mark.parametrize("caso", ["primero", "siguiente"])
def test_estado_api_no_se_comparte_entre_casos(cliente_api, caso):
    # Cada caso deja un plan; el siguiente debe empezar sin él y sin llamadas previas.
    assert servicio._planes_pendientes == {}
    assert servicio._agente is None
    assert not historial.registro_temporal.conoce_hilo("hilo-aislamiento")
    assert historial.registro_temporal.obtener_pregunta("hilo-aislamiento") is None
    historial.registro_temporal.guardar_pregunta("hilo-aislamiento", "Pregunta pendiente de este caso")
    respuesta = cliente_api.post(
        "/ask",
        json={"pregunta": "Ruta de Sol a Atocha", "thread_id": "hilo-aislamiento", "auto_aprobar": False},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["pendiente_hitl"] is True
    assert "hilo-aislamiento" in servicio._planes_pendientes
    assert servicio._agente.llamadas == [("procesar_turno", "hilo-aislamiento", "Ruta de Sol a Atocha")]


@pytest.mark.parametrize("caso", ["primero", "siguiente"])
def test_datos_aislados_entre_casos_y_compartidos_entre_sesiones(sesiones_api, caso):
    # Un mismo identificador prueba aislamiento entre casos y persistencia entre sesiones del caso.
    with sesiones_api() as escritura:
        assert escritura.exec(select(Conversation)).all() == []
        assert escritura.exec(select(Message)).all() == []
        save_closed_turn(escritura, "mismo-hilo", "Pregunta de prueba", "Respuesta de prueba")
    with sesiones_api() as lectura:
        assert lectura is not escritura
        assert [m.content for m in get_thread_messages(lectura, "mismo-hilo")] == [
            "Pregunta de prueba", "Respuesta de prueba",
        ]


def test_sesion_no_confirmada_se_revierte_al_cerrar(sesiones_api):
    with sesiones_api() as escritura:
        escritura.add(Conversation(thread_id="sin-commit"))
        escritura.flush()
    with sesiones_api() as lectura:
        assert lectura.get(Conversation, "sin-commit") is None


def test_arranque_y_sesiones_usan_sqlite_local(entorno_api, sesiones_api, motor_api):
    import src.db as db

    # El doble de arranque y la dependencia existente deben apuntar a la misma base del caso.
    assert db.get_engine() is motor_api
    assert motor_api.dialect.name == "sqlite"
    db.create_db_and_tables()
    session_generator = db.get_session()
    try:
        escritura = next(session_generator)
        save_closed_turn(escritura, "arranque", "Pregunta", "Respuesta")
    finally:
        session_generator.close()
    with sesiones_api() as lectura:
        assert len(get_thread_messages(lectura, "arranque")) == 2
