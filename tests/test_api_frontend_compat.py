"""SPEC-016 T19: frontend SPEC-015 sin modificar su rama ni hacer HTTP real.

Optativo: SPEC016_FRONTEND_DIR apunta a copias revisadas de front.py y api_http.py.
"""
import importlib.util
import io
import os
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def frontend_real(cliente_api, monkeypatch):
    raw = os.getenv("SPEC016_FRONTEND_DIR")
    if not raw:
        pytest.skip("requiere copia revisada de SPEC-015 mediante SPEC016_FRONTEND_DIR")
    carpeta = Path(raw)
    assert (carpeta / "front.py").is_file() and (carpeta / "api_http.py").is_file()
    nombre = "src.clientes.api_http"
    spec = importlib.util.spec_from_file_location(nombre, carpeta / "api_http.py")
    modulo = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, nombre, modulo)
    spec.loader.exec_module(modulo)

    def transporte(request, timeout=None):
        # Solo este transporte se sustituye: UI y cliente HTTP son los de SPEC-015.
        partes = urlsplit(request.full_url)
        assert partes.hostname == "testserver"
        ruta = partes.path + ("?" + partes.query if partes.query else "")
        respuesta = cliente_api.request(request.get_method(), ruta, content=request.data,
                                        headers=dict(request.header_items()))
        if respuesta.status_code >= 400:
            raise HTTPError(request.full_url, respuesta.status_code, "Error API", {}, io.BytesIO(respuesta.content))
        return io.BytesIO(respuesta.content)

    monkeypatch.setattr(modulo, "urlopen", transporte)
    monkeypatch.setenv("API_BASE_URL", "http://testserver")
    monkeypatch.setenv("API_KEY", "spec016_clave_ficticia")
    rutas_originales = sys.path[:]
    try:
        yield AppTest.from_file(str(carpeta / "front.py"), default_timeout=15).run()
    finally:
        sys.path[:] = rutas_originales


@pytest.mark.parametrize("decision", ["Aprobar", "Rechazar", "automatico"])
def test_frontend_real_pregunta_decision_recarga(frontend_real, decision):
    interfaz = frontend_real
    assert not interfaz.exception
    next(b for b in interfaz.button if b.label == "Comprobar estado").click().run()
    assert interfaz.session_state["health_status"] is True
    if decision == "automatico":
        interfaz.checkbox[0].check().run()
    pregunta = "Ruta de Sol a Atocha"
    interfaz.chat_input[0].set_value(pregunta).run()
    assert not interfaz.exception
    hilo = interfaz.session_state["thread_id"]
    if decision != "automatico":
        assert interfaz.session_state["pending_hitl"] is True
        next(b for b in interfaz.button if b.label == decision).click().run()
        assert interfaz.session_state["decision_result"]["done"] is (decision == "Aprobar")
    else:
        assert interfaz.session_state["ask_result"]["done"] is True
    assert not interfaz.exception
    assert interfaz.session_state["history_error"] is None
    next(b for b in interfaz.button if b.label == "Nueva conversación").click().run()
    interfaz.text_input[0].set_value(hilo).run()
    next(b for b in interfaz.button if b.label == "Cargar conversación").click().run()
    assert not interfaz.exception
    assert interfaz.session_state["thread_id"] == hilo
    assert len(interfaz.session_state["messages"]) == 2
    assert interfaz.session_state["messages"][0]["content"] == pregunta
    assert [m["orden"] for m in interfaz.session_state["messages"]] == [1, 2]
