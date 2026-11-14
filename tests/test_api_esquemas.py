"""Tests de los formatos de datos de la API (spec 013, RF-4, RF-5, RF-10 y RF-11).

Comprueban las reglas de cada formulario antes de que la API los use: qué campos
son obligatorios, cuáles son opcionales y qué valores se rechazan.
"""
import pytest
from pydantic import ValidationError

from src.api.esquemas import ApproveIn, AskIn, AskOut, MessageOut


def test_ask_valido_con_valores_por_defecto():
    # Con solo la pregunta basta: el identificador es opcional y la aprobación automática viene activada.
    entrada = AskIn(pregunta="¿Hasta qué hora hay metro?")
    assert entrada.thread_id is None
    assert entrada.auto_aprobar is True


@pytest.mark.parametrize("pregunta", ["", "   "])
def test_ask_rechaza_pregunta_vacia(pregunta):
    # Una pregunta vacía o de solo espacios no debe llegar nunca al agente (RF-5).
    with pytest.raises(ValidationError):
        AskIn(pregunta=pregunta)


def test_ask_rechaza_pregunta_ausente_o_de_tipo_incorrecto():
    # Sin pregunta, con un número en lugar de texto o con un valor que no es sí/no: error de validación.
    with pytest.raises(ValidationError):
        AskIn()
    with pytest.raises(ValidationError):
        AskIn(pregunta=123)
    with pytest.raises(ValidationError):
        AskIn(pregunta="hola", auto_aprobar="quizás")


def test_ask_out_valores_por_defecto():
    # Sin plan pendiente ni fallo, la respuesta lleva la lista de planes vacía y el error en nulo.
    salida = AskOut(respuesta="ok", thread_id="abc", done=True, pendiente_hitl=False)
    assert salida.plan == []
    assert salida.error is None


def test_approve_plan_id_es_opcional():
    # El plan elegido solo se indica cuando hay varios planes pendientes (RF-11).
    decision = ApproveIn(thread_id="abc", aprobado=True)
    assert decision.plan_id is None


def test_approve_exige_thread_id_y_decision():
    # Sin conversación o sin decisión no se puede aprobar ni rechazar nada.
    with pytest.raises(ValidationError):
        ApproveIn(aprobado=True)
    with pytest.raises(ValidationError):
        ApproveIn(thread_id="abc")


def test_message_out_tiene_autor_texto_y_orden():
    # Formato del historial que pide el enunciado: quién habla, qué dice y en qué posición.
    mensaje = MessageOut(role="user", content="hola", orden=1)
    assert (mensaje.role, mensaje.content, mensaje.orden) == ("user", "hola", 1)
    