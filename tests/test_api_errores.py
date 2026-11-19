"""Tests de los errores de la API (spec 013, T7: RF-14) y de la ruta de historial reservada.

Usan el agente simulado, que puede fallar a propósito: no gastan API.
"""

import config
from src.api import servicio
from src.clientes.cargar import GrafoNoDisponible
from src.clientes.grafo_falso import GrafoFalso

CLAVE_PRUEBA = "clave-de-prueba"


def test_fallo_del_agente_en_ask_da_500_generico(cliente_api, monkeypatch):
    # RF-14: el mensaje es el genérico y no se cuela el detalle interno del fallo.
    monkeypatch.setattr(servicio, "_agente", GrafoFalso(fallar=True))
    r = cliente_api.post("/ask", json={"pregunta": "Hola metro"})
    assert r.status_code == 500
    assert r.json()["detail"] == config.API_ERROR_INTERNO
    assert "fallo simulado" not in r.text
    assert CLAVE_PRUEBA not in r.text


def test_fallo_del_agente_en_approve_da_500_generico(cliente_api, monkeypatch):
    monkeypatch.setattr(servicio, "_agente", GrafoFalso(fallar=True))
    r = cliente_api.post("/approve", json={"thread_id": "e1", "aprobado": True})
    assert r.status_code == 500
    assert r.json()["detail"] == config.API_ERROR_INTERNO
    assert CLAVE_PRUEBA not in r.text


def test_agente_no_disponible_da_500_generico(cliente_api, monkeypatch):
    # Si no se puede cargar el agente, tampoco se muestran detalles internos.
    def sin_grafo(*args, **kwargs):
        raise GrafoNoDisponible("detalle interno del grafo")

    monkeypatch.setattr(servicio, "cargar_agente", sin_grafo)
    r = cliente_api.post("/ask", json={"pregunta": "Hola metro"})
    assert r.status_code == 500
    assert r.json()["detail"] == config.API_ERROR_INTERNO
    assert "detalle interno" not in r.text
    assert CLAVE_PRUEBA not in r.text


def test_historial_inexistente_da_404(cliente_api):
    r = cliente_api.get("/threads/abc/messages")
    assert r.status_code == 404
    assert r.json()["detail"] == config.API_CONVERSACION_NO_ENCONTRADA


def test_esquema_incluye_la_ruta_de_mensajes(cliente_api):
    assert "/threads/{thread_id}/messages" in cliente_api.get("/openapi.json").json()["paths"]
