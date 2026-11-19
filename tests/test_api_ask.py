"""Tests de POST /ask sin aprobación automática (spec 013, T4: RF-4, RF-5, RF-6 y RF-15).

Usan el agente simulado y una clave fija de prueba, así que no gastan API.
"""
import pytest
from fastapi.testclient import TestClient

import config
from app import app
from src.api import servicio

cliente = TestClient(app)
CLAVE_PRUEBA = "clave-de-prueba"


def preguntar(datos):
    return cliente.post("/ask", params={"api_key": CLAVE_PRUEBA}, json=datos)


@pytest.fixture(autouse=True)
def agente_simulado(monkeypatch):
    # Todos los tests usan el agente simulado y arrancan con un agente nuevo, sin memoria previa.
    monkeypatch.setenv(config.VARIABLE_MODO_SIMULADO, config.VALOR_MODO_SIMULADO)
    monkeypatch.setattr(config, "API_KEY", CLAVE_PRUEBA)
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 10_000)
    monkeypatch.setattr(servicio, "_agente", None)


def test_pregunta_sin_plan_devuelve_respuesta_y_cierra():
    # Una consulta que no es de ruta termina en el mismo turno (RF-4 y RF-15).
    r = preguntar({"pregunta": "¿A qué hora cierra el metro?"})
    assert r.status_code == 200
    datos = r.json()
    assert datos["respuesta"].startswith("[Simulado]")
    assert datos["done"] is True
    assert datos["pendiente_hitl"] is False
    assert datos["plan"] == []
    assert datos["error"] is None
    assert datos["thread_id"]


def test_pregunta_de_ruta_deja_el_plan_pendiente():
    # Con la aprobación automática apagada, el plan se devuelve pendiente (RF-4 y RF-8).
    datos = preguntar(
        {"pregunta": "Quiero una ruta de Sol a Atocha", "auto_aprobar": False}
    ).json()
    assert datos["pendiente_hitl"] is True
    assert datos["done"] is False
    assert len(datos["plan"]) == 1


def test_sin_thread_id_se_crea_uno_nuevo_cada_vez():
    # RF-6: si falta el identificador, la API lo inventa y es distinto en cada conversación.
    primero = preguntar({"pregunta": "Hola metro"}).json()["thread_id"]
    segundo = preguntar({"pregunta": "Hola metro"}).json()["thread_id"]
    assert primero and segundo and primero != segundo


def test_thread_id_recibido_se_respeta_y_llega_al_agente():
    # El identificador enviado vuelve igual y es el que usa el agente.
    datos = preguntar({"pregunta": "Hola metro", "thread_id": "abc-123"}).json()
    assert datos["thread_id"] == "abc-123"
    assert servicio._agente.llamadas == [("procesar_turno", "abc-123", "Hola metro")]


@pytest.mark.parametrize("pregunta", ["", "   "])
def test_pregunta_vacia_da_422(pregunta):
    # RF-5: una pregunta vacía o solo con espacios no es válida.
    assert preguntar({"pregunta": pregunta}).status_code == 422


def test_sin_pregunta_da_422():
    assert preguntar({}).status_code == 422


def test_rechazo_del_agente_se_convierte_en_error(monkeypatch):
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
    datos = preguntar({"pregunta": "Hola metro"}).json()
    assert datos["error"] == "Hay un plan pendiente en esta conversación."


def test_esquema_incluye_ask():
    assert "/ask" in cliente.get("/openapi.json").json()["paths"]
