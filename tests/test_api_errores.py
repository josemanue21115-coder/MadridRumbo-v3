"""Tests de los errores de la API (spec 013, T7: RF-14) y de la ruta de historial reservada.

Usan el agente simulado, que puede fallar a propósito: no gastan API.
"""
import pytest
from fastapi.testclient import TestClient

import config
from app import app
from src.api import servicio
from src.clientes.cargar import GrafoNoDisponible
from src.clientes.grafo_falso import GrafoFalso

cliente = TestClient(app)


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    # Agente simulado y sin memoria de otros tests.
    monkeypatch.setenv(config.VARIABLE_MODO_SIMULADO, config.VALOR_MODO_SIMULADO)
    monkeypatch.setattr(servicio, "_agente", None)
    monkeypatch.setattr(servicio, "_planes_pendientes", {})


def test_fallo_del_agente_en_ask_da_500_generico(monkeypatch):
    # RF-14: el mensaje es el genérico y no se cuela el detalle interno del fallo.
    monkeypatch.setattr(servicio, "_agente", GrafoFalso(fallar=True))
    r = cliente.post("/ask", json={"pregunta": "Hola metro"})
    assert r.status_code == 500
    assert r.json()["detail"] == config.API_ERROR_INTERNO
    assert "fallo simulado" not in r.text


def test_fallo_del_agente_en_approve_da_500_generico(monkeypatch):
    monkeypatch.setattr(servicio, "_agente", GrafoFalso(fallar=True))
    r = cliente.post("/approve", json={"thread_id": "e1", "aprobado": True})
    assert r.status_code == 500
    assert r.json()["detail"] == config.API_ERROR_INTERNO


def test_agente_no_disponible_da_500_generico(monkeypatch):
    # Si no se puede cargar el agente, tampoco se muestran detalles internos.
    def sin_grafo(*args, **kwargs):
        raise GrafoNoDisponible("detalle interno del grafo")

    monkeypatch.setattr(servicio, "cargar_agente", sin_grafo)
    r = cliente.post("/ask", json={"pregunta": "Hola metro"})
    assert r.status_code == 500
    assert r.json()["detail"] == config.API_ERROR_INTERNO
    assert "detalle interno" not in r.text


def test_ruta_de_mensajes_esta_reservada_y_responde_501():
    # La ruta existe, pero el historial lo implementa la persona 2 (base de datos).
    r = cliente.get("/threads/abc/messages")
    assert r.status_code == 501
    assert r.json()["detail"] == config.API_MENSAJES_NO_IMPLEMENTADO


def test_esquema_incluye_la_ruta_de_mensajes():
    assert "/threads/{thread_id}/messages" in cliente.get("/openapi.json").json()["paths"]
    