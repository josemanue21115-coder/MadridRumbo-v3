"""Pruebas del timeout exclusivo de POST /ask (spec 017)."""
import json
import logging
import time

import pytest
from fastapi.testclient import TestClient

import config
from app import app
from src.api import servicio
from src.api.esquemas import AskOut


CLAVE_PRUEBA = "clave-timeout-de-prueba"
cliente = TestClient(app)
MENSAJE_TIMEOUT = "El turno ha superado el tiempo máximo permitido. Inténtalo de nuevo."


@pytest.fixture(autouse=True)
def entorno_timeout_aislado(monkeypatch, entorno_api):
    """Usa una clave y cuota de prueba para no depender del entorno ni de otros tests."""
    monkeypatch.setattr(config, "API_KEY", CLAVE_PRUEBA)
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 10_000)
    monkeypatch.setattr(config, "ASK_TIMEOUT_SECONDS", 1)


def test_timeout_predeterminado_si_la_variable_no_esta_configurada(monkeypatch):
    monkeypatch.delenv("ASK_TIMEOUT_SECONDS", raising=False)

    assert config._entero_positivo_entorno("ASK_TIMEOUT_SECONDS", 300) == 300


@pytest.mark.parametrize("valor", ["no-es-un-entero", "0", "-1"])
def test_timeout_invalido_usa_300_segundos(monkeypatch, valor):
    monkeypatch.setenv("ASK_TIMEOUT_SECONDS", valor)

    assert config._entero_positivo_entorno("ASK_TIMEOUT_SECONDS", 300) == 300


def test_ask_lento_devuelve_504_con_mensaje_y_sin_secreto(monkeypatch, caplog):
    monkeypatch.setattr(config, "ASK_TIMEOUT_SECONDS", 0.01)
    caplog.set_level(logging.INFO)

    def turno_lento(_datos, _sesion=None):
        time.sleep(0.05)
        return AskOut(
            respuesta="Respuesta simulada",
            thread_id="hilo-timeout",
            done=True,
            pendiente_hitl=False,
        )

    monkeypatch.setattr(servicio, "preguntar", turno_lento)
    respuesta = cliente.post(
        "/ask?api_key=" + CLAVE_PRUEBA,
        json={"pregunta": "Consulta simulada", "auto_aprobar": False},
    )

    assert respuesta.status_code == 504
    assert respuesta.json()["detail"] == MENSAJE_TIMEOUT
    assert CLAVE_PRUEBA not in respuesta.text
    eventos_peticion = [
        json.loads(registro.getMessage())
        for registro in caplog.records
        if registro.name == "src.api.logs_peticion"
    ]
    assert len(eventos_peticion) == 1
    assert eventos_peticion[0]["event"] == "protected_request"
    assert eventos_peticion[0]["status_code"] == 504
    assert eventos_peticion[0]["thread_id"] is None
    assert CLAVE_PRUEBA not in json.dumps(eventos_peticion[0])
    assert not any(
        registro.name == "app" and "timeout" in registro.getMessage().lower()
        for registro in caplog.records
    )


def test_approve_no_aplica_el_timeout_de_ask(monkeypatch):
    monkeypatch.setattr(config, "ASK_TIMEOUT_SECONDS", 0.01)

    def aprobacion_lenta(datos, _sesion=None):
        time.sleep(0.05)
        return AskOut(
            respuesta="Decisión simulada",
            thread_id=datos.thread_id,
            done=True,
            pendiente_hitl=False,
        )

    monkeypatch.setattr(servicio, "aprobar", aprobacion_lenta)
    respuesta = cliente.post(
        "/approve?api_key=" + CLAVE_PRUEBA,
        json={"thread_id": "hilo-timeout", "aprobado": True},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["respuesta"] == "Decisión simulada"


def test_historial_no_aplica_el_timeout_de_ask(monkeypatch):
    monkeypatch.setattr(config, "ASK_TIMEOUT_SECONDS", 0.01)

    respuesta = cliente.get(
        "/threads/hilo-timeout/messages?api_key=" + CLAVE_PRUEBA
    )

    assert respuesta.status_code == 404
