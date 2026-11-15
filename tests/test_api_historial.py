"""SPEC-016 T2: validación de identificadores previa al agente y a SQL."""
from urllib.parse import quote
from uuid import UUID

import pytest
from sqlalchemy import event

from src.api import servicio


@pytest.fixture
def llamadas_externas(cliente_api, motor_api, monkeypatch):
    """Cuenta accesos posteriores al arranque aislado de cada cliente de prueba."""
    llamadas = {"agente": 0, "sql": 0}
    obtener_agente = servicio.obtener_agente

    def contar_agente():
        llamadas["agente"] += 1
        return obtener_agente()

    def contar_sql(*args):
        llamadas["sql"] += 1

    monkeypatch.setattr(servicio, "obtener_agente", contar_agente)
    event.listen(motor_api, "before_cursor_execute", contar_sql)
    try:
        yield llamadas
    finally:
        event.remove(motor_api, "before_cursor_execute", contar_sql)


@pytest.mark.parametrize("ruta", ["/ask", "/approve", "historial"])
@pytest.mark.parametrize("thread_id", ["", "   ", "\t", "x" * 129])
def test_thread_invalido_422_sin_consultas(cliente_api, llamadas_externas, ruta, thread_id):
    if ruta == "historial":
        respuesta = cliente_api.get(f"/threads/{quote(thread_id, safe='')}/messages")
        # Un segmento ausente no llega a ser un parámetro de la ruta.
        esperado = 404 if thread_id == "" else 422
    else:
        cuerpo = {"thread_id": thread_id}
        cuerpo.update({"pregunta": "Hola metro"} if ruta == "/ask" else {"aprobado": True})
        respuesta = cliente_api.post(ruta, json=cuerpo)
        esperado = 422
    assert respuesta.status_code == esperado
    assert llamadas_externas == {"agente": 0, "sql": 0}


@pytest.mark.parametrize("ruta", ["/ask", "/approve"])
@pytest.mark.parametrize("thread_id", [123, False, [], {}])
def test_thread_de_tipo_incorrecto_422(cliente_api, llamadas_externas, ruta, thread_id):
    cuerpo = {"thread_id": thread_id}
    cuerpo.update({"pregunta": "Hola metro"} if ruta == "/ask" else {"aprobado": True})
    respuesta = cliente_api.post(ruta, json=cuerpo)
    assert respuesta.status_code == 422
    assert llamadas_externas == {"agente": 0, "sql": 0}


@pytest.mark.parametrize("thread_id", ["x" * 128, "ñ" * 128, " hilo con espacios "])
def test_thread_valido_se_conserva_en_pregunta_y_decision(cliente_api, thread_id):
    pendiente = cliente_api.post(
        "/ask",
        json={"pregunta": "Ruta de Sol a Atocha", "thread_id": thread_id, "auto_aprobar": False},
    )
    assert pendiente.status_code == 200
    assert pendiente.json()["thread_id"] == thread_id
    assert pendiente.json()["pendiente_hitl"] is True
    final = cliente_api.post("/approve", json={"thread_id": thread_id, "aprobado": True})
    assert final.status_code == 200
    assert final.json()["thread_id"] == thread_id
    assert final.json()["done"] is True
    assert set(final.json()) == {"respuesta", "thread_id", "done", "pendiente_hitl", "plan", "error"}


@pytest.mark.parametrize("thread_id", ["x" * 128, "ñ" * 128, " hilo con espacios "])
def test_historial_thread_valido_llega_a_la_ruta(cliente_api, thread_id):
    respuesta = cliente_api.get(f"/threads/{quote(thread_id, safe='')}/messages")
    # T2 solo valida la entrada; la conexión de historial sustituirá este 501 en T4.
    assert respuesta.status_code == 501


@pytest.mark.parametrize("campo", [{}, {"thread_id": None}])
def test_ask_sin_identificador_genera_uuid(cliente_api, campo):
    cuerpo = {"pregunta": "Hola metro", **campo}
    primero = cliente_api.post("/ask", json=cuerpo)
    segundo = cliente_api.post("/ask", json=cuerpo)
    assert primero.status_code == segundo.status_code == 200
    identificador = primero.json()["thread_id"]
    assert UUID(identificador).version == 4
    assert identificador != segundo.json()["thread_id"]


def test_approve_no_admite_identificador_null(cliente_api, llamadas_externas):
    respuesta = cliente_api.post("/approve", json={"thread_id": None, "aprobado": True})
    assert respuesta.status_code == 422
    assert llamadas_externas == {"agente": 0, "sql": 0}
