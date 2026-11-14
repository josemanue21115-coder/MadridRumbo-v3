"""Tests de POST /approve (spec 013, T6: RF-10, RF-11, RF-12 y RF-13).

Usan el agente simulado: no gastan API. Cada test usa su propio thread_id.
"""
import pytest
from fastapi.testclient import TestClient

import config
from app import app
from src.api import servicio

cliente = TestClient(app)

RUTA = "Quiero una ruta de Sol a Atocha"
DOS_RUTAS = "Quiero dos rutas alternativas de Sol a Atocha"


@pytest.fixture(autouse=True)
def agente_simulado(monkeypatch):
    # Agente simulado y limpio en cada test, sin conversaciones ni planes anteriores.
    monkeypatch.setenv(config.VARIABLE_MODO_SIMULADO, config.VALOR_MODO_SIMULADO)
    monkeypatch.setattr(servicio, "_agente", None)
    monkeypatch.setattr(servicio, "_planes_pendientes", {})


def preguntar_sin_aprobar(pregunta, thread_id):
    # Deja el plan esperando, apagando la aprobación automática.
    return cliente.post(
        "/ask", json={"pregunta": pregunta, "thread_id": thread_id, "auto_aprobar": False}
    ).json()


def test_aprobar_el_plan_pendiente():
    # RF-10: aprobar devuelve el mismo formato que /ask, con la conversación terminada.
    preguntar_sin_aprobar(RUTA, "a1")
    r = cliente.post("/approve", json={"thread_id": "a1", "aprobado": True})
    assert r.status_code == 200
    datos = r.json()
    assert datos["respuesta"].startswith("[Simulado] Plan aprobado")
    assert datos["thread_id"] == "a1"
    assert datos["done"] is True
    assert datos["pendiente_hitl"] is False
    assert datos["error"] is None


def test_con_varios_planes_hace_falta_elegir_uno():
    # RF-11: sin plan_id la API avisa en `error`; con plan_id aprueba el elegido.
    preguntar_sin_aprobar(DOS_RUTAS, "a2")
    sin_elegir = cliente.post("/approve", json={"thread_id": "a2", "aprobado": True}).json()
    assert sin_elegir["error"] and "identificador" in sin_elegir["error"]
    eligiendo = cliente.post(
        "/approve", json={"thread_id": "a2", "aprobado": True, "plan_id": "ruta-2"}
    ).json()
    assert "ruta-2" in eligiendo["respuesta"]
    assert eligiendo["error"] is None


def test_rechazar_el_plan_deja_continuar_la_conversacion():
    # RF-12: rechazar no es un error; la conversación sigue abierta.
    preguntar_sin_aprobar(RUTA, "a3")
    datos = cliente.post("/approve", json={"thread_id": "a3", "aprobado": False}).json()
    assert "rechazado" in datos["respuesta"]
    assert datos["error"] is None
    assert datos["pendiente_hitl"] is False
    assert cliente.post("/ask", json={"pregunta": "Hola metro", "thread_id": "a3"}).status_code == 200


def test_sin_plan_pendiente_avisa_en_error():
    # RF-13: aprobar donde no hay nada esperando no rompe la API; avisa en `error`.
    datos = cliente.post("/approve", json={"thread_id": "a4", "aprobado": True}).json()
    assert datos["error"] and "plan pendiente" in datos["error"]


@pytest.mark.parametrize(
    "cuerpo",
    [{"aprobado": True}, {"thread_id": "a5"}, {"thread_id": "", "aprobado": True}],
)
def test_datos_incompletos_dan_422(cuerpo):
    # Falta el identificador, falta la decisión o el identificador está vacío.
    assert cliente.post("/approve", json=cuerpo).status_code == 422


def test_esquema_incluye_approve():
    assert "/approve" in cliente.get("/openapi.json").json()["paths"]
    