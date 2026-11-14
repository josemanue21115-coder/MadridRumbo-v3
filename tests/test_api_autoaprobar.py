"""Tests de la aprobación automática en POST /ask (spec 013, T5: RF-7, RF-8 y RF-9).

Usan el agente simulado: no gastan API. Se comprueban las llamadas que recibe el agente
para saber si la API aprobó el plan o lo dejó pendiente.
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
    # Agente simulado y limpio en cada test, sin memoria de conversaciones anteriores.
    monkeypatch.setenv(config.VARIABLE_MODO_SIMULADO, config.VALOR_MODO_SIMULADO)
    monkeypatch.setattr(servicio, "_agente", None)


def test_con_un_solo_plan_se_aprueba_solo_por_defecto():
    # RF-7: sin indicar nada, auto_aprobar vale verdadero y el único plan se aprueba.
    datos = cliente.post("/ask", json={"pregunta": RUTA, "thread_id": "t1"}).json()
    assert datos["respuesta"].startswith("[Simulado] Plan aprobado")
    assert datos["done"] is True
    assert datos["pendiente_hitl"] is False
    assert servicio._agente.llamadas == [
        ("procesar_turno", "t1", RUTA),
        ("aprobar_plan", "t1", True),
    ]


def test_con_auto_aprobar_falso_el_plan_queda_pendiente():
    # RF-8: la API nunca aprueba si se le pide que no lo haga.
    datos = cliente.post(
        "/ask", json={"pregunta": RUTA, "thread_id": "t2", "auto_aprobar": False}
    ).json()
    assert datos["pendiente_hitl"] is True
    assert len(datos["plan"]) == 1
    assert [llamada[0] for llamada in servicio._agente.llamadas] == ["procesar_turno"]


def test_con_varios_planes_no_se_aprueba_ninguno():
    # RF-9: si hay varios planes, la API no elige por la persona.
    datos = cliente.post(
        "/ask", json={"pregunta": DOS_RUTAS, "thread_id": "t3", "auto_aprobar": True}
    ).json()
    assert datos["pendiente_hitl"] is True
    assert len(datos["plan"]) == 2
    assert [llamada[0] for llamada in servicio._agente.llamadas] == ["procesar_turno"]


def test_sin_plan_no_se_intenta_aprobar_nada():
    # Una consulta que no es de ruta no tiene nada que aprobar.
    datos = cliente.post("/ask", json={"pregunta": "Hola metro", "thread_id": "t4"}).json()
    assert datos["done"] is True
    assert [llamada[0] for llamada in servicio._agente.llamadas] == ["procesar_turno"]