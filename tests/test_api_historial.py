"""SPEC-016 T2/T3: identificadores, contexto temporal y formato del historial."""
from urllib.parse import quote
from uuid import UUID

import pytest
from sqlalchemy import event

import config
from src.api import servicio


@pytest.fixture
def adaptador_historial():
    # El módulo se importa aquí para mantener ejecutables los casos anteriores de T2.
    from src.api import historial

    return historial


def test_registro_conserva_pregunta_original_y_aisla_hilos(adaptador_historial):
    registro = adaptador_historial.RegistroTemporal()
    registro.guardar_pregunta("uno", "Pregunta original")
    registro.guardar_pregunta("dos", "Pregunta diferente")
    registro.guardar_pregunta("uno", "Otra pregunta que no debe sustituirla")
    assert registro.conoce_hilo("uno")
    assert registro.conoce_hilo("dos")
    assert not registro.conoce_hilo("desconocido")
    assert registro.obtener_pregunta("uno") == "Pregunta original"
    assert registro.obtener_pregunta("dos") == "Pregunta diferente"
    assert registro.obtener_pregunta("desconocido") is None


def test_registro_finaliza_turno_sin_olvidar_hilo(adaptador_historial):
    registro = adaptador_historial.RegistroTemporal()
    registro.guardar_pregunta("uno", "Primera")
    registro.guardar_pregunta("dos", "Ajena")
    registro.finalizar_turno("uno")
    assert registro.conoce_hilo("uno")
    assert registro.obtener_pregunta("uno") is None
    assert registro.obtener_pregunta("dos") == "Ajena"
    registro.guardar_pregunta("uno", "Siguiente turno")
    assert registro.obtener_pregunta("uno") == "Siguiente turno"
    registro.finalizar_turno("desconocido")
    assert not registro.conoce_hilo("desconocido")


def test_registro_temporal_limpia_estado(adaptador_historial):
    registro = adaptador_historial.RegistroTemporal()
    registro.guardar_pregunta("pendiente", "Pregunta")
    registro.registrar_hilo("sin-pregunta")
    otro = adaptador_historial.RegistroTemporal()
    assert not otro.conoce_hilo("pendiente")
    otro.guardar_pregunta("otro", "Pregunta ajena")
    registro.limpiar()
    registro.limpiar()
    assert not registro.conoce_hilo("pendiente")
    assert not registro.conoce_hilo("sin-pregunta")
    assert registro.obtener_pregunta("pendiente") is None
    assert otro.obtener_pregunta("otro") == "Pregunta ajena"


def test_campos_publicos_historial(adaptador_historial, sesiones_api):
    from src.history import get_thread_messages, save_closed_turn

    with sesiones_api() as sesion:
        save_closed_turn(sesion, "uno", "¿Pregunta?", "Respuesta con ñ")
        originales = get_thread_messages(sesion, "uno")
        datos_previos = [m.model_dump() for m in originales]
        mensajes = adaptador_historial.leer_historial(sesion, "uno")
        assert [m.model_dump() for m in mensajes] == [
            {"role": "user", "content": "¿Pregunta?", "orden": 1},
            {"role": "assistant", "content": "Respuesta con ñ", "orden": 2},
        ]
        assert [m.model_dump() for m in originales] == datos_previos


def test_orden_consecutivo_con_ids_intercalados(adaptador_historial, sesiones_api):
    from src.history import get_thread_messages, save_closed_turn

    with sesiones_api() as sesion:
        save_closed_turn(sesion, "uno", "Pregunta 1", "Respuesta 1")
        save_closed_turn(sesion, "dos", "Pregunta ajena", "Respuesta ajena")
        save_closed_turn(sesion, "uno", "Pregunta 2", "Respuesta 2")
        assert [m.id for m in get_thread_messages(sesion, "uno")] == [1, 2, 5, 6]
        mensajes = adaptador_historial.leer_historial(sesion, "uno")
        assert [m.orden for m in mensajes] == [1, 2, 3, 4]
        assert [m.content for m in mensajes] == ["Pregunta 1", "Respuesta 1", "Pregunta 2", "Respuesta 2"]


def test_hilos_separados(adaptador_historial, sesiones_api):
    from src.history import save_closed_turn

    with sesiones_api() as sesion:
        save_closed_turn(sesion, "uno", "Pregunta uno", "Respuesta uno")
        save_closed_turn(sesion, "dos", "Pregunta dos", "Respuesta dos")
        assert [m.content for m in adaptador_historial.leer_historial(sesion, "uno")] == [
            "Pregunta uno", "Respuesta uno",
        ]
        assert [m.content for m in adaptador_historial.leer_historial(sesion, "dos")] == [
            "Pregunta dos", "Respuesta dos",
        ]


def test_hilo_conocido_temporal_no_crea_filas(adaptador_historial, sesiones_api, entorno_api):
    from sqlmodel import select

    from src.models import Conversation, Message

    registro = adaptador_historial.registro_temporal
    registro.guardar_pregunta("pendiente", "Pregunta pendiente")
    with sesiones_api() as sesion:
        assert adaptador_historial.es_hilo_conocido(sesion, "pendiente")
        assert adaptador_historial.leer_historial(sesion, "pendiente") == []
        assert sesion.exec(select(Conversation)).all() == []
        assert sesion.exec(select(Message)).all() == []


def test_hilo_persistido_es_conocido_sin_registro_temporal(adaptador_historial, sesiones_api, entorno_api):
    from src.history import save_closed_turn
    from src.models import Conversation

    with sesiones_api() as sesion:
        save_closed_turn(sesion, "guardado", "Pregunta", "Respuesta")
        sesion.add(Conversation(thread_id="vacio"))
        sesion.commit()
        assert not adaptador_historial.registro_temporal.conoce_hilo("guardado")
        assert adaptador_historial.es_hilo_conocido(sesion, "guardado")
        assert adaptador_historial.es_hilo_conocido(sesion, "vacio")
        assert adaptador_historial.leer_historial(sesion, "vacio") == []


def test_hilo_desconocido_no_crea_filas(adaptador_historial, sesiones_api, entorno_api):
    from sqlmodel import select

    from src.models import Conversation, Message

    with sesiones_api() as sesion:
        assert not adaptador_historial.es_hilo_conocido(sesion, "inexistente")
        assert adaptador_historial.leer_historial(sesion, "inexistente") == []
        assert not adaptador_historial.registro_temporal.conoce_hilo("inexistente")
        assert sesion.exec(select(Conversation)).all() == []
        assert sesion.exec(select(Message)).all() == []


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
    # El identificador es válido y llega a la búsqueda, aunque el hilo no exista.
    assert respuesta.status_code == 404


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


def test_historial_guardado_200(cliente_api, sesiones_api):
    from src.history import save_closed_turn

    with sesiones_api() as sesion:
        save_closed_turn(sesion, "uno", "Pregunta 1", "Respuesta 1")
        save_closed_turn(sesion, "dos", "Ajena", "Ajena")
        save_closed_turn(sesion, "uno", "Pregunta 2", "Respuesta 2")
    respuesta = cliente_api.get("/threads/uno/messages")
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"role": "user", "content": "Pregunta 1", "orden": 1},
        {"role": "assistant", "content": "Respuesta 1", "orden": 2},
        {"role": "user", "content": "Pregunta 2", "orden": 3},
        {"role": "assistant", "content": "Respuesta 2", "orden": 4},
    ]


def test_desconocido_404(cliente_api, sesiones_api):
    from sqlmodel import select
    from src.models import Conversation

    respuesta = cliente_api.get("/threads/inexistente/messages")
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Conversación no encontrada"}
    with sesiones_api() as sesion:
        assert sesion.exec(select(Conversation)).all() == []


def test_conocido_sin_mensajes_200_vacio(cliente_api):
    from src.api.historial import registro_temporal

    registro_temporal.guardar_pregunta("pendiente", "Pregunta original")
    respuesta = cliente_api.get("/threads/pendiente/messages")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


@pytest.mark.parametrize("operacion", ["es_hilo_conocido", "leer_historial"])
def test_lectura_fallida_500(cliente_api, monkeypatch, operacion):
    from src.api import historial

    historial.registro_temporal.registrar_hilo("conocido")

    def fallo(*args):
        raise RuntimeError("detalle SQL sensible ficticio")

    monkeypatch.setattr(historial, operacion, fallo)
    respuesta = cliente_api.get("/threads/conocido/messages")
    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": config.API_ERROR_INTERNO}
    assert "SQL" not in respuesta.text


@pytest.mark.parametrize("status", [404, 422])
def test_errores_http_deliberados_se_conservan(status):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as capturada:
        with servicio._fallos_como_500():
            raise HTTPException(status_code=status, detail="Error esperado")
    assert capturada.value.status_code == status
