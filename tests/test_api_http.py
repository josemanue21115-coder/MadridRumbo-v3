"""Contrato del cliente HTTP de Streamlit, sin abrir conexiones de red."""

import io
import json
import urllib.error
from urllib.parse import parse_qs, urlparse

import pytest

from src.clientes.api_http import APIHttpClient, APIHttpError, APIConnectionError


class RespuestaFalsa:
    """Respuesta mínima compatible con urllib.request.urlopen."""

    def __init__(self, datos, status=200):
        self.datos = json.dumps(datos).encode("utf-8")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.datos


def preparar_urlopen(monkeypatch, resultado=None, error=None):
    llamadas = []

    def urlopen(request, timeout=None):
        llamadas.append((request, timeout))
        if error:
            raise error
        return resultado or RespuestaFalsa({"estado": "ok"})

    monkeypatch.setattr("src.clientes.api_http.urlopen", urlopen)
    return llamadas


def test_url_base_por_defecto_y_configurada(monkeypatch):
    llamadas = preparar_urlopen(monkeypatch)

    monkeypatch.delenv("API_BASE_URL", raising=False)
    APIHttpClient().health()
    monkeypatch.setenv("API_BASE_URL", "https://api.ejemplo.test/")
    APIHttpClient().health()
    monkeypatch.setenv("API_BASE_URL", "   ")
    APIHttpClient().health()

    assert llamadas[0][0].full_url == "http://127.0.0.1:8000/health"
    assert llamadas[1][0].full_url == "https://api.ejemplo.test/health"
    assert llamadas[2][0].full_url == "http://127.0.0.1:8000/health"


def test_health_es_publico_y_devuelve_json(monkeypatch):
    llamadas = preparar_urlopen(monkeypatch, RespuestaFalsa({"estado": "ok"}))

    assert APIHttpClient().health() == {"estado": "ok"}
    request = llamadas[0][0]
    assert request.get_method() == "GET"
    assert urlparse(request.full_url).path == "/health"
    assert "api_key" not in parse_qs(urlparse(request.full_url).query)


@pytest.mark.parametrize("metodo", ["ask", "approve", "messages"])
def test_rutas_protegidas_incluyen_api_key_en_query(monkeypatch, metodo):
    llamadas = preparar_urlopen(monkeypatch)
    cliente = APIHttpClient(api_key="clave-de-prueba")

    if metodo == "ask":
        cliente.ask("¿Hasta qué hora hay metro?", auto_aprobar=False)
    elif metodo == "approve":
        cliente.approve("hilo-1", aprobado=True)
    else:
        cliente.messages("hilo-1")

    query = parse_qs(urlparse(llamadas[0][0].full_url).query)
    assert query == {"api_key": ["clave-de-prueba"]}


def test_ask_envia_json_y_omite_thread_id_si_no_se_indica(monkeypatch):
    llamadas = preparar_urlopen(monkeypatch, RespuestaFalsa({"respuesta": "Hola"}))

    APIHttpClient(api_key="k").ask("Hola", auto_aprobar=False)

    request = llamadas[0][0]
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {"pregunta": "Hola", "auto_aprobar": False}


def test_ask_incluye_thread_id_existente(monkeypatch):
    llamadas = preparar_urlopen(monkeypatch)

    APIHttpClient(api_key="k").ask("Sigue", thread_id="hilo-1", auto_aprobar=True)

    assert json.loads(llamadas[0][0].data) == {
        "pregunta": "Sigue",
        "thread_id": "hilo-1",
        "auto_aprobar": True,
    }


def test_approve_envia_decision_y_plan_opcional(monkeypatch):
    llamadas = preparar_urlopen(monkeypatch)
    APIHttpClient(api_key="k").approve("hilo-1", aprobado=False, plan_id="ruta-2")

    request = llamadas[0][0]
    assert request.get_method() == "POST"
    assert urlparse(request.full_url).path == "/approve"
    assert json.loads(request.data) == {
        "thread_id": "hilo-1",
        "aprobado": False,
        "plan_id": "ruta-2",
    }


def test_approve_omite_plan_id_si_no_se_indica(monkeypatch):
    llamadas = preparar_urlopen(monkeypatch)
    APIHttpClient(api_key="k").approve("hilo-1", aprobado=True)

    assert json.loads(llamadas[0][0].data) == {"thread_id": "hilo-1", "aprobado": True}


def test_historial_consulta_thread_y_devuelve_json(monkeypatch):
    mensajes = [{"role": "user", "content": "Hola", "orden": 1}]
    llamadas = preparar_urlopen(monkeypatch, RespuestaFalsa(mensajes))

    assert APIHttpClient(api_key="k").messages("hilo con espacio") == mensajes
    request = llamadas[0][0]
    assert request.get_method() == "GET"
    assert urlparse(request.full_url).path == "/threads/hilo%20con%20espacio/messages"


def test_error_http_se_convierte_a_error_cliente_con_estado(monkeypatch):
    respuesta = io.BytesIO(b'{"detail":"No encontrado"}')
    error = urllib.error.HTTPError("https://api.test/threads/hilo/messages", 404, "Not Found", {}, respuesta)
    preparar_urlopen(monkeypatch, error=error)

    with pytest.raises(APIHttpError) as captura:
        APIHttpClient(api_key="k").messages("hilo")

    assert captura.value.status_code == 404
    assert "No encontrado" in str(captura.value)


def test_error_de_red_se_convierte_a_error_cliente(monkeypatch):
    preparar_urlopen(monkeypatch, error=OSError("conexión rechazada"))

    with pytest.raises(APIConnectionError, match="conexión rechazada"):
        APIHttpClient().health()


def test_json_invalido_se_convierte_a_error_cliente(monkeypatch):
    respuesta = RespuestaFalsa({})
    respuesta.datos = b"no es json"
    preparar_urlopen(monkeypatch, resultado=respuesta)

    with pytest.raises(APIHttpError, match="JSON"):
        APIHttpClient().health()
