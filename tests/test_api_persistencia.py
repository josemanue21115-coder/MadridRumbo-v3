"""SPEC-016: recorrido HTTP de cierre y persistencia sin LLM ni APIs de transporte."""
import pytest


def preguntar(cliente, hilo="hilo", pregunta="Hola metro", **extra):
    return cliente.post("/ask", json={"pregunta": pregunta, "thread_id": hilo, **extra})


def mensajes(cliente, hilo="hilo"):
    respuesta = cliente.get(f"/threads/{hilo}/messages")
    assert respuesta.status_code == 200
    return respuesta.json()


def test_ask_directo_guarda_par(cliente_api):
    respuesta = preguntar(cliente_api)
    assert respuesta.status_code == 200
    assert mensajes(cliente_api) == [
        {"role": "user", "content": "Hola metro", "orden": 1},
        {"role": "assistant", "content": respuesta.json()["respuesta"], "orden": 2},
    ]
    preguntar(cliente_api, pregunta="Otra pregunta")
    assert len(mensajes(cliente_api)) == 4


def test_uuid_devuelto_es_el_persistido(cliente_api):
    respuesta = cliente_api.post("/ask", json={"pregunta": "Hola metro"})
    assert respuesta.status_code == 200
    assert len(mensajes(cliente_api, respuesta.json()["thread_id"])) == 2


def test_200_solo_despues_del_commit(cliente_api, motor_api):
    from sqlalchemy import event

    commits = []
    def confirmar(connection):
        commits.append(True)
    event.listen(motor_api, "commit", confirmar)
    try:
        respuesta = preguntar(cliente_api)
        assert respuesta.status_code == 200
        assert commits == [True]
    finally:
        event.remove(motor_api, "commit", confirmar)


def test_pendiente_no_guarda_y_conserva_historial_previo(cliente_api):
    from src.api.historial import registro_temporal

    pendiente = preguntar(cliente_api, pregunta="Ruta de Sol a Atocha", auto_aprobar=False)
    assert pendiente.json()["pendiente_hitl"] is True
    assert mensajes(cliente_api) == []
    assert registro_temporal.obtener_pregunta("hilo") == "Ruta de Sol a Atocha"
    preguntar(cliente_api, hilo="otro")
    antes = mensajes(cliente_api, "otro")
    preguntar(cliente_api, hilo="otro", pregunta="Dos rutas de Sol a Atocha", auto_aprobar=False)
    assert mensajes(cliente_api, "otro") == antes


def test_rechazo_control_conserva_historial_y_pregunta(cliente_api, monkeypatch):
    from src.api import historial, servicio

    preguntar(cliente_api, pregunta="Ruta original de Sol a Atocha", auto_aprobar=False)
    def rechazar(*args):
        return {"respuesta": "Resuelve el plan pendiente", "done": False, "hitl_pendiente": False,
                "plan": [], "traza": [], "log": [{"tipo": "control", "resultado": "rechazado"}]}
    monkeypatch.setattr(servicio._agente, "procesar_turno", rechazar)
    respuesta = preguntar(cliente_api, pregunta="No debe sustituir la pregunta original")
    assert respuesta.json()["error"]
    assert historial.registro_temporal.obtener_pregunta("hilo") == "Ruta original de Sol a Atocha"
    assert "hilo" in servicio._planes_pendientes
    assert mensajes(cliente_api) == []


@pytest.mark.parametrize("pregunta,plan_id", [("Ruta de Sol a Atocha", None), ("Dos rutas de Sol a Atocha", "ruta-2")])
def test_approve_guarda_pregunta_original(cliente_api, pregunta, plan_id):
    from src.api.historial import registro_temporal

    preguntar(cliente_api, pregunta=pregunta, auto_aprobar=False)
    cuerpo = {"thread_id": "hilo", "aprobado": True}
    if plan_id:
        cuerpo["plan_id"] = plan_id
    respuesta = cliente_api.post("/approve", json=cuerpo)
    assert respuesta.status_code == 200
    assert respuesta.json()["done"] is True
    assert [m["content"] for m in mensajes(cliente_api)] == [pregunta, respuesta.json()["respuesta"]]
    assert registro_temporal.obtener_pregunta("hilo") is None


def test_autoaprobar_guarda_un_solo_par(cliente_api):
    from src.api import historial, servicio

    respuesta = preguntar(cliente_api, pregunta="Ruta de Sol a Atocha")
    assert respuesta.status_code == 200
    assert respuesta.json()["done"] is True
    assert [m["content"] for m in mensajes(cliente_api)] == ["Ruta de Sol a Atocha", respuesta.json()["respuesta"]]
    assert [c[0] for c in servicio._agente.llamadas] == ["procesar_turno", "aprobar_plan"]
    assert historial.registro_temporal.obtener_pregunta("hilo") is None


def test_autoaprobar_varios_planes_no_guarda(cliente_api):
    from src.api import servicio

    respuesta = preguntar(cliente_api, pregunta="Dos rutas de Sol a Atocha")
    assert respuesta.json()["pendiente_hitl"] is True
    assert mensajes(cliente_api) == []
    assert [c[0] for c in servicio._agente.llamadas] == ["procesar_turno"]


@pytest.mark.parametrize("varios", [False, True])
def test_ultimo_rechazo_guarda_par_con_done_false(cliente_api, varios):
    pregunta = "Dos rutas de Sol a Atocha" if varios else "Ruta de Sol a Atocha"
    preguntar(cliente_api, pregunta=pregunta, auto_aprobar=False)
    if varios:
        parcial = cliente_api.post("/approve", json={"thread_id": "hilo", "aprobado": False, "plan_id": "ruta-1"})
        assert parcial.json()["pendiente_hitl"] is True
        assert mensajes(cliente_api) == []
    final = cliente_api.post("/approve", json={"thread_id": "hilo", "aprobado": False})
    assert final.status_code == 200
    assert final.json()["done"] is False
    assert final.json()["pendiente_hitl"] is False
    assert [m["content"] for m in mensajes(cliente_api)] == [pregunta, final.json()["respuesta"]]
    preguntar(cliente_api, pregunta="Ahora otra pregunta")
    assert len(mensajes(cliente_api)) == 4


@pytest.mark.parametrize("aprobado", [True, False])
def test_approve_repetido_no_duplica(cliente_api, aprobado):
    preguntar(cliente_api, pregunta="Ruta de Sol a Atocha", auto_aprobar=False)
    cuerpo = {"thread_id": "hilo", "aprobado": aprobado}
    assert cliente_api.post("/approve", json=cuerpo).status_code == 200
    antes = mensajes(cliente_api)
    repetida = cliente_api.post("/approve", json=cuerpo)
    assert repetida.json()["error"]
    assert mensajes(cliente_api) == antes


@pytest.mark.parametrize("plan_id", [None, "no-existe"])
def test_seleccion_invalida_conserva_turno_pendiente(cliente_api, plan_id):
    from src.api import historial

    pregunta = "Dos rutas de Sol a Atocha"
    preguntar(cliente_api, pregunta=pregunta, auto_aprobar=False)
    cuerpo = {"thread_id": "hilo", "aprobado": True}
    if plan_id:
        cuerpo["plan_id"] = plan_id
    respuesta = cliente_api.post("/approve", json=cuerpo)
    assert respuesta.json()["error"]
    assert historial.registro_temporal.obtener_pregunta("hilo") == pregunta
    assert mensajes(cliente_api) == []
    cuerpo["plan_id"] = "ruta-2"
    assert cliente_api.post("/approve", json=cuerpo).json()["done"] is True
    assert len(mensajes(cliente_api)) == 2


def test_decision_sin_plan_no_crea_conversacion(cliente_api):
    respuesta = cliente_api.post("/approve", json={"thread_id": "inexistente", "aprobado": True})
    assert respuesta.json()["error"]
    assert cliente_api.get("/threads/inexistente/messages").status_code == 404
