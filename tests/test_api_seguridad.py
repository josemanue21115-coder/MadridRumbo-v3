"""Pruebas aisladas de la configuración de seguridad de la API (spec 017)."""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from time import monotonic as reloj_real

import pytest
from fastapi.testclient import TestClient

import config
from app import app
from src.api import servicio
from src.api import seguridad
from src.clientes.grafo_falso import GrafoFalso


RAIZ = Path(__file__).resolve().parents[1]
CLAVE_PRUEBA = "clave-de-prueba"
cliente = TestClient(app)


@pytest.fixture(autouse=True)
def entorno_api_aislado(monkeypatch, entorno_api):
    """Usa credenciales y agente falsos en las pruebas HTTP."""
    monkeypatch.setattr(config, "API_KEY", CLAVE_PRUEBA)
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 10_000)
    monkeypatch.setattr(servicio, "_agente", GrafoFalso())
    monkeypatch.setattr(servicio, "_planes_pendientes", {})


def _solicitar(metodo, ruta, *, params=None, datos=None):
    if metodo == "post":
        return cliente.post(ruta, params=params, json=datos)
    return cliente.get(ruta, params=params)


def _leer_configuracion_aislada(**variables):
    """Carga config.py en un proceso sin ejecutar dotenv ni leer el .env local."""
    entorno = os.environ.copy()
    for nombre in ("API_KEY", "RATE_LIMIT_PER_MINUTE", "ASK_TIMEOUT_SECONDS"):
        entorno.pop(nombre, None)
    entorno.update(variables)

    codigo = """
import json
import runpy
import sys
import types

dotenv = types.ModuleType('dotenv')
dotenv.load_dotenv = lambda: None
sys.modules['dotenv'] = dotenv
config = runpy.run_path('config.py', run_name='configuracion_aislada')
print(json.dumps({
    'API_KEY': config.get('API_KEY'),
    'RATE_LIMIT_PER_MINUTE': config.get('RATE_LIMIT_PER_MINUTE'),
    'ASK_TIMEOUT_SECONDS': config.get('ASK_TIMEOUT_SECONDS'),
}))
"""
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env=entorno,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(resultado.stdout)


def test_configuracion_usa_valores_del_entorno():
    valores = _leer_configuracion_aislada(
        API_KEY="clave-de-prueba",
        RATE_LIMIT_PER_MINUTE="7",
        ASK_TIMEOUT_SECONDS="12",
    )

    assert valores == {
        "API_KEY": "clave-de-prueba",
        "RATE_LIMIT_PER_MINUTE": 7,
        "ASK_TIMEOUT_SECONDS": 12,
    }


def test_configuracion_usa_valores_predeterminados_si_faltan():
    valores = _leer_configuracion_aislada()

    assert valores["API_KEY"] in (None, "")
    assert valores["RATE_LIMIT_PER_MINUTE"] == 30
    assert valores["ASK_TIMEOUT_SECONDS"] == 300


def test_configuracion_usa_valores_predeterminados_si_limites_son_invalidos():
    valores = _leer_configuracion_aislada(
        RATE_LIMIT_PER_MINUTE="no-es-un-entero",
        ASK_TIMEOUT_SECONDS="0",
    )

    assert valores["RATE_LIMIT_PER_MINUTE"] == 30
    assert valores["ASK_TIMEOUT_SECONDS"] == 300


def test_env_example_documenta_configuracion_sin_secretos():
    lineas = (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines()
    valores = {
        linea.partition("=")[0]: linea.partition("=")[2]
        for linea in lineas
        if "=" in linea and not linea.lstrip().startswith("#")
    }

    assert valores.get("API_KEY") == ""
    assert valores.get("RATE_LIMIT_PER_MINUTE") == "30"
    assert valores.get("ASK_TIMEOUT_SECONDS") == "300"


@pytest.mark.parametrize(
    ("metodo", "ruta", "datos", "estado_esperado"),
    [
        ("post", "/ask", {"pregunta": "Hola", "auto_aprobar": False}, 200),
        ("post", "/approve", {"thread_id": "hilo-test", "aprobado": False}, 200),
        ("get", "/threads/hilo-test/messages", None, 404),
    ],
)
def test_clave_valida_permite_acceder_a_rutas_protegidas(
    metodo, ruta, datos, estado_esperado
):
    respuesta = _solicitar(metodo, ruta, params={"api_key": CLAVE_PRUEBA}, datos=datos)

    assert respuesta.status_code == estado_esperado


@pytest.mark.parametrize(
    ("metodo", "ruta", "datos"),
    [
        ("post", "/ask", {"pregunta": "Hola"}),
        ("post", "/approve", {"thread_id": "hilo-test", "aprobado": False}),
        ("get", "/threads/hilo-test/messages", None),
    ],
)
@pytest.mark.parametrize("api_key", [None, "clave-incorrecta"])
def test_clave_ausente_o_incorrecta_devuelve_401(metodo, ruta, datos, api_key):
    params = {} if api_key is None else {"api_key": api_key}
    respuesta = _solicitar(metodo, ruta, params=params, datos=datos)

    assert respuesta.status_code == 401
    assert "clave-incorrecta" not in respuesta.text


@pytest.mark.parametrize(
    ("metodo", "ruta", "datos"),
    [
        ("post", "/ask", {"pregunta": "Hola"}),
        ("post", "/approve", {"thread_id": "hilo-test", "aprobado": False}),
        ("get", "/threads/hilo-test/messages", None),
    ],
)
def test_clave_del_servicio_no_configurada_devuelve_503(metodo, ruta, datos, monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")
    respuesta = _solicitar(metodo, ruta, params={"api_key": CLAVE_PRUEBA}, datos=datos)

    assert respuesta.status_code == 503
    assert CLAVE_PRUEBA not in respuesta.text


def test_rutas_publicas_responden_sin_clave(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")

    assert cliente.get("/health").status_code == 200
    assert cliente.get("/docs").status_code == 200
    assert cliente.get("/openapi.json").status_code == 200


@pytest.mark.parametrize(
    ("ruta", "metodo"),
    [
        ("/ask", "post"),
        ("/approve", "post"),
        ("/threads/{thread_id}/messages", "get"),
    ],
)
def test_openapi_declara_api_key_como_parametro_de_query(ruta, metodo):
    esquema = cliente.get("/openapi.json").json()
    parametros = esquema["paths"][ruta][metodo]["parameters"]

    assert any(
        parametro["name"] == "api_key" and parametro["in"] == "query"
        for parametro in parametros
    )


def test_limite_compartido_se_aplica_entre_rutas(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(config, "API_KEY", "clave-limite-compartido")

    primera = cliente.get(
        "/threads/hilo-test/messages", params={"api_key": config.API_KEY}
    )
    segunda = cliente.post(
        "/approve",
        params={"api_key": config.API_KEY},
        json={"thread_id": "hilo-test", "aprobado": False},
    )
    tercera = cliente.post(
        "/ask",
        params={"api_key": config.API_KEY},
        json={"pregunta": "Hola", "auto_aprobar": False},
    )

    assert primera.status_code == 404
    assert segunda.status_code == 200
    assert tercera.status_code == 429
    assert config.API_KEY not in tercera.text


def test_limite_usa_ventana_movil_de_60_segundos(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(config, "API_KEY", "clave-ventana-movil")
    reloj = {"ahora": (int(reloj_real() // 60) + 1) * 60 - 1}
    monkeypatch.setattr(seguridad, "monotonic", lambda: reloj["ahora"], raising=False)

    def consultar_historial():
        return cliente.get(
            "/threads/hilo-test/messages", params={"api_key": config.API_KEY}
        )

    assert consultar_historial().status_code == 404
    reloj["ahora"] += 0.5
    assert consultar_historial().status_code == 404
    reloj["ahora"] += 0.5
    assert consultar_historial().status_code == 429
    reloj["ahora"] += 59.6
    assert consultar_historial().status_code == 404


def test_intentos_sin_clave_comparten_el_mismo_limite(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr(config, "API_KEY", "clave-missing-compartido")
    reloj = {"ahora": reloj_real() + 3600}
    monkeypatch.setattr(seguridad, "monotonic", lambda: reloj["ahora"], raising=False)

    primera = cliente.post(
        "/ask", json={"pregunta": "Hola", "auto_aprobar": False}
    )
    segunda = cliente.get("/threads/hilo-test/messages")

    assert primera.status_code == 401
    assert segunda.status_code == 429


def test_limite_intentos_con_clave_invalida_consumen_cuota_de_esa_clave(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr(config, "API_KEY", "clave-correcta-del-test")
    reloj = {"ahora": reloj_real() + 7200}
    monkeypatch.setattr(seguridad, "monotonic", lambda: reloj["ahora"], raising=False)
    clave_invalida = "clave-invalida-contabilizada"

    primera = cliente.get(
        "/threads/hilo-test/messages", params={"api_key": clave_invalida}
    )
    segunda = cliente.post(
        "/approve",
        params={"api_key": clave_invalida},
        json={"thread_id": "hilo-test", "aprobado": False},
    )

    assert primera.status_code == 401
    assert segunda.status_code == 429
    assert clave_invalida not in primera.text
    assert clave_invalida not in segunda.text


def test_access_log_sanea_query_y_no_duplica_rutas_protegidas():
    logger_acceso = logging.getLogger("uvicorn.access")
    filtro = next(
        elemento
        for elemento in logger_acceso.filters
        if elemento.__class__.__name__ == "_FiltroAccessLog"
    )
    registro_protegido = logger_acceso.makeRecord(
        name="uvicorn.access",
        level=logging.INFO,
        fn=__file__,
        lno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=(
            "127.0.0.1:12345",
            "POST",
            f"/ask?api_key={CLAVE_PRUEBA}",
            "1.1",
            200,
        ),
        exc_info=None,
    )
    registro_publico = logger_acceso.makeRecord(
        name="uvicorn.access",
        level=logging.INFO,
        fn=__file__,
        lno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=(
            "127.0.0.1:12345",
            "GET",
            f"/health?trace_id={CLAVE_PRUEBA}",
            "1.1",
            200,
        ),
        exc_info=None,
    )

    assert filtro.filter(registro_protegido) is False
    assert "?api_key=" not in registro_protegido.getMessage()
    assert CLAVE_PRUEBA not in registro_protegido.getMessage()

    assert filtro.filter(registro_publico) is True
    assert "?trace_id=" not in registro_publico.getMessage()
    assert CLAVE_PRUEBA not in registro_publico.getMessage()
