"""Contrato inicial de logs de peticiones protegidas (spec 019, T1)."""
import asyncio
import json
import logging
from threading import Event

import pytest
from fastapi.testclient import TestClient

import config
from app import app
from src.api import servicio
from src.api.esquemas import AskOut
from src.api.logs_peticion import RegistroPeticionesProtegidas
from src.clientes.grafo_falso import GrafoFalso


CLAVE_PRUEBA = "clave-logs-test"
cliente = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def entorno_logs_aislado(monkeypatch, caplog, entorno_api):
    """Aísla autenticación, cuota y logs entre peticiones de prueba."""
    monkeypatch.setattr(config, "API_KEY", CLAVE_PRUEBA)
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 10_000)
    caplog.set_level(logging.INFO)
    caplog.clear()


def _eventos_peticion(caplog):
    """Devuelve los eventos JSON de petición, ignorando otros mensajes del logger."""
    eventos = []
    for registro in caplog.records:
        try:
            evento = json.loads(registro.getMessage())
        except (TypeError, json.JSONDecodeError):
            continue
        if evento.get("event") == "protected_request":
            eventos.append(evento)
    return eventos


def _comprobar_evento(caplog, respuesta, metodo, ruta, thread_id):
    eventos = _eventos_peticion(caplog)

    assert len(eventos) == 1
    evento = eventos[0]
    assert evento["method"] == metodo
    assert evento["route"] == ruta
    assert evento["thread_id"] == thread_id
    assert isinstance(evento["duration_ms"], (int, float))
    assert evento["duration_ms"] >= 0
    assert evento["status_code"] == respuesta.status_code


def test_ask_registra_campos_y_thread_id_generado(monkeypatch, caplog):
    """Un ask sin ID de entrada registra el identificador que devuelve el servicio."""
    monkeypatch.setattr(
        servicio,
        "preguntar",
        lambda _datos, _sesion=None: AskOut(
            respuesta="Respuesta simulada",
            thread_id="hilo-generado",
            done=True,
            pendiente_hitl=False,
        ),
    )

    respuesta = cliente.post(
        "/ask?api_key=" + CLAVE_PRUEBA,
        json={"pregunta": "Consulta simulada", "auto_aprobar": False},
    )

    assert respuesta.status_code == 200
    _comprobar_evento(caplog, respuesta, "POST", "/ask", "hilo-generado")


def test_approve_registra_campos_y_thread_id(monkeypatch, caplog):
    monkeypatch.setattr(
        servicio,
        "aprobar",
        lambda datos, _sesion=None: AskOut(
            respuesta="Decisión simulada",
            thread_id=datos.thread_id,
            done=True,
            pendiente_hitl=False,
        ),
    )

    respuesta = cliente.post(
        "/approve?api_key=" + CLAVE_PRUEBA,
        json={"thread_id": "hilo-aprobado", "aprobado": True},
    )

    assert respuesta.status_code == 200
    _comprobar_evento(caplog, respuesta, "POST", "/approve", "hilo-aprobado")


def test_historial_registra_campos_y_thread_id_concreto(caplog):
    respuesta = cliente.get(
        "/threads/hilo-historial/messages?api_key=" + CLAVE_PRUEBA
    )

    assert respuesta.status_code == 404
    _comprobar_evento(
        caplog,
        respuesta,
        "GET",
        "/threads/hilo-historial/messages",
        "hilo-historial",
    )


def test_fallo_antes_de_obtener_thread_id_registra_null(monkeypatch, caplog):
    """Si el servicio falla antes de devolver el ID, el evento usa null."""
    from fastapi import HTTPException

    def fallar_antes_del_id(_datos):
        raise HTTPException(status_code=500, detail="Fallo simulado")

    monkeypatch.setattr(servicio, "preguntar", fallar_antes_del_id)

    respuesta = cliente.post(
        "/ask?api_key=" + CLAVE_PRUEBA,
        json={"pregunta": "Consulta simulada", "auto_aprobar": False},
    )

    assert respuesta.status_code == 500
    _comprobar_evento(caplog, respuesta, "POST", "/ask", None)


def test_error_401_registra_estado_y_thread_id_null(caplog):
    respuesta = cliente.post(
        "/ask",
        json={"pregunta": "Consulta simulada", "auto_aprobar": False},
    )

    assert respuesta.status_code == 401
    _comprobar_evento(caplog, respuesta, "POST", "/ask", None)


def test_error_429_registra_estado(monkeypatch, caplog):
    clave_limitada = "clave-rate-limit-logs-test"
    monkeypatch.setattr(config, "API_KEY", clave_limitada)
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 1)
    ruta = "/threads/hilo-limite/messages"
    assert cliente.get(ruta, params={"api_key": clave_limitada}).status_code == 404
    caplog.clear()

    respuesta = cliente.get(ruta, params={"api_key": clave_limitada})

    assert respuesta.status_code == 429
    _comprobar_evento(
        caplog, respuesta, "GET", ruta, "hilo-limite"
    )


def test_error_503_registra_estado(monkeypatch, caplog):
    monkeypatch.setattr(config, "API_KEY", "")
    respuesta = cliente.get(
        "/threads/hilo-no-configurado/messages",
        params={"api_key": CLAVE_PRUEBA},
    )

    assert respuesta.status_code == 503
    _comprobar_evento(
        caplog,
        respuesta,
        "GET",
        "/threads/hilo-no-configurado/messages",
        "hilo-no-configurado",
    )


def test_error_504_registra_estado(monkeypatch, caplog):
    monkeypatch.setattr(config, "ASK_TIMEOUT_SECONDS", 0.005)

    def turno_lento(_datos, _sesion=None):
        Event().wait(0.05)
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
    _comprobar_evento(caplog, respuesta, "POST", "/ask", None)


def test_error_500_registra_estado_y_mensaje_generico(monkeypatch, caplog):
    monkeypatch.setattr(servicio, "_agente", GrafoFalso(fallar=True))
    monkeypatch.setattr(servicio, "_planes_pendientes", {})

    respuesta = cliente.post(
        "/ask?api_key=" + CLAVE_PRUEBA,
        json={"pregunta": "Consulta simulada", "auto_aprobar": False},
    )

    assert respuesta.status_code == 500
    assert respuesta.json()["detail"] == config.API_ERROR_INTERNO
    _comprobar_evento(caplog, respuesta, "POST", "/ask", None)


def test_validacion_422_registra_peticion_y_thread_id_null(caplog):
    respuesta = cliente.post(
        "/ask?api_key=" + CLAVE_PRUEBA,
        json={"pregunta": "   ", "auto_aprobar": False},
    )

    assert respuesta.status_code == 422
    _comprobar_evento(caplog, respuesta, "POST", "/ask", None)


def test_fallo_antes_de_enviar_respuesta_registra_estado_null(caplog):
    async def aplicacion_fallida(_scope, _receive, _send):
        raise RuntimeError("Fallo antes de la respuesta")

    async def recibir():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def enviar(_mensaje):
        return None

    alcance = {
        "type": "http",
        "method": "POST",
        "path": "/ask",
        "state": {},
    }

    with pytest.raises(RuntimeError, match="Fallo antes de la respuesta"):
        asyncio.run(
            RegistroPeticionesProtegidas(aplicacion_fallida)(
                alcance, recibir, enviar
            )
        )

    eventos = _eventos_peticion(caplog)
    assert len(eventos) == 1
    assert eventos[0]["method"] == "POST"
    assert eventos[0]["route"] == "/ask"
    assert eventos[0]["thread_id"] is None
    assert isinstance(eventos[0]["duration_ms"], (int, float))
    assert eventos[0]["duration_ms"] >= 0
    assert eventos[0]["status_code"] is None


def _texto_logs_del_servicio(caplog):
    """Formatea solo logs de la API/servidor, incluyendo posibles tracebacks."""
    nombres = {
        "app",
        "src.api.logs_peticion",
        "src.api.servicio",
        "uvicorn.access",
    }
    formato = logging.Formatter("%(name)s %(message)s")
    return "\n".join(
        formato.format(registro)
        for registro in caplog.records
        if registro.name in nombres
    )


def test_logs_de_exito_no_contienen_secretos_ni_texto_conversacional(
    monkeypatch, caplog
):
    marcadores = {
        "api_key": "SECRETO_API_KEY_UNICO",
        "openai": "SECRETO_OPENAI_UNICO",
        "gemini": "SECRETO_GEMINI_UNICO",
        "database": "SECRETO_DATABASE_URL_UNICO",
        "pregunta": "TEXTO_PREGUNTA_PRIVADA_UNICO",
        "respuesta": "TEXTO_RESPUESTA_PRIVADA_UNICO",
    }
    monkeypatch.setattr(config, "API_KEY", marcadores["api_key"])
    monkeypatch.setattr(config, "OPENAI_API_KEY", marcadores["openai"])
    monkeypatch.setattr(config, "GEMINI_API_KEY", marcadores["gemini"])
    monkeypatch.setattr(config, "DATABASE_URL", marcadores["database"])
    monkeypatch.setattr(
        servicio,
        "preguntar",
        lambda _datos, _sesion=None: AskOut(
            respuesta=marcadores["respuesta"],
            thread_id="hilo-privado",
            done=True,
            pendiente_hitl=False,
        ),
    )

    respuesta = cliente.post(
        "/ask",
        params={"api_key": marcadores["api_key"]},
        json={"pregunta": marcadores["pregunta"], "auto_aprobar": False},
    )

    assert respuesta.status_code == 200
    texto_logs = _texto_logs_del_servicio(caplog)
    assert all(marcador not in texto_logs for marcador in marcadores.values())
    _comprobar_evento(
        caplog, respuesta, "POST", "/ask", "hilo-privado"
    )


def test_log_de_excepcion_no_contiene_detalle_sensible(monkeypatch, caplog):
    api_key = "SECRETO_API_KEY_ERROR_UNICO"
    texto_pregunta = "TEXTO_PREGUNTA_ERROR_PRIVADO_UNICO"
    detalle_excepcion = "DETALLE_EXCEPCION_SENSIBLE_UNICO"
    monkeypatch.setattr(config, "API_KEY", api_key)

    class GrafoConFalloSensible:
        def procesar_turno(self, *_args):
            raise RuntimeError(detalle_excepcion)

    monkeypatch.setattr(servicio, "_agente", GrafoConFalloSensible())
    monkeypatch.setattr(servicio, "_planes_pendientes", {})

    respuesta = cliente.post(
        "/ask",
        params={"api_key": api_key},
        json={"pregunta": texto_pregunta, "auto_aprobar": False},
    )

    assert respuesta.status_code == 500
    assert respuesta.json()["detail"] == config.API_ERROR_INTERNO
    texto_logs = _texto_logs_del_servicio(caplog)
    assert api_key not in texto_logs
    assert texto_pregunta not in texto_logs
    assert detalle_excepcion not in texto_logs
