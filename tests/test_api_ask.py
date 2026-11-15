"""Tests de POST /ask sin aprobación automática (spec 013, T4: RF-4, RF-5, RF-6 y RF-15).

Usan el agente simulado, así que no gastan API ni dependen de claves.
"""
import pytest

from src.api import servicio


def test_pregunta_sin_plan_devuelve_respuesta_y_cierra(cliente_api):
    # Una consulta que no es de ruta termina en el mismo turno (RF-4 y RF-15).
    r = cliente_api.post("/ask", json={"pregunta": "¿A qué hora cierra el metro?"})
    assert r.status_code == 200
    datos = r.json()
    assert datos["respuesta"].startswith("[Simulado]")
    assert datos["done"] is True
    assert datos["pendiente_hitl"] is False
    assert datos["plan"] == []
    assert datos["error"] is None
    assert datos["thread_id"]


def test_pregunta_de_ruta_deja_el_plan_pendiente(cliente_api):
    # Con la aprobación automática apagada, el plan se devuelve pendiente (RF-4 y RF-8).
    datos = cliente_api.post(
        "/ask", json={"pregunta": "Quiero una ruta de Sol a Atocha", "auto_aprobar": False}
    ).json()
    assert datos["pendiente_hitl"] is True
    assert datos["done"] is False
    assert len(datos["plan"]) == 1


def test_sin_thread_id_se_crea_uno_nuevo_cada_vez(cliente_api):
    # RF-6: si falta el identificador, la API lo inventa y es distinto en cada conversación.
    primero = cliente_api.post("/ask", json={"pregunta": "Hola metro"}).json()["thread_id"]
    segundo = cliente_api.post("/ask", json={"pregunta": "Hola metro"}).json()["thread_id"]
    assert primero and segundo and primero != segundo


def test_thread_id_recibido_se_respeta_y_llega_al_agente(cliente_api):
    # El identificador enviado vuelve igual y es el que usa el agente.
    datos = cliente_api.post("/ask", json={"pregunta": "Hola metro", "thread_id": "abc-123"}).json()
    assert datos["thread_id"] == "abc-123"
    assert servicio._agente.llamadas == [("procesar_turno", "abc-123", "Hola metro")]


@pytest.mark.parametrize("pregunta", ["", "   "])
def test_pregunta_vacia_da_422(cliente_api, pregunta):
    # RF-5: una pregunta vacía o solo con espacios no es válida.
    assert cliente_api.post("/ask", json={"pregunta": pregunta}).status_code == 422


def test_sin_pregunta_da_422(cliente_api):
    assert cliente_api.post("/ask", json={}).status_code == 422


def test_rechazo_del_agente_se_convierte_en_error(cliente_api, monkeypatch):
    # Si el agente rechaza la consulta por una regla de control, el motivo va en `error`.
    class AgenteQueRechaza:
        def procesar_turno(self, estado, mensaje, thread_id):
            return {
                "respuesta": "Hay un plan pendiente en esta conversación.",
                "plan": [],
                "log": [{"tipo": "control", "resultado": "rechazado"}],
                "traza": [],
                "hitl_pendiente": False,
                "done": False,
            }

    monkeypatch.setattr(servicio, "_agente", AgenteQueRechaza())
    datos = cliente_api.post("/ask", json={"pregunta": "Hola metro"}).json()
    assert datos["error"] == "Hay un plan pendiente en esta conversación."


def test_esquema_incluye_ask(cliente_api):
    assert "/ask" in cliente_api.get("/openapi.json").json()["paths"]
