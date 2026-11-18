"""Pruebas de configuración CORS para la spec 018."""

import json
import os
import subprocess
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
ORIGENES_CLASE = (
    "http://127.0.0.1:8000,http://localhost:8000,"
    "http://127.0.0.1:8501,http://localhost:3000"
)


def _leer_config_cors(**variables: str) -> list[str] | None:
    """Carga config.py aislada sin permitir que dotenv lea el .env local."""
    entorno = os.environ.copy()
    entorno.pop("CORS_ORIGINS", None)
    entorno.update(variables)

    codigo = """
import json
import runpy
import sys
import types

dotenv = types.ModuleType("dotenv")
dotenv.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv
config = runpy.run_path("config.py", run_name="configuracion_aislada")
print(json.dumps(config.get("CORS_ORIGINS")))
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


def test_config_cors_separa_origenes():
    origenes = _leer_config_cors(
        CORS_ORIGINS="http://localhost:8501,https://ejemplo.test"
    )

    assert origenes == ["http://localhost:8501", "https://ejemplo.test"]


def test_config_cors_ausente_o_vacia():
    assert _leer_config_cors() == []
    assert _leer_config_cors(CORS_ORIGINS="") == []
    assert _leer_config_cors(CORS_ORIGINS="   ") == []


def test_config_cors_recorta_espacios_e_ignora_vacios():
    origenes = _leer_config_cors(
        CORS_ORIGINS="  http://localhost:8501, ,https://ejemplo.test,, "
    )

    assert origenes == ["http://localhost:8501", "https://ejemplo.test"]


def test_env_example_documenta_cors():
    lineas = (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines()

    assert (
        "# Orígenes del front / clientes web (separados por coma). Cambiad según el entorno."
        in lineas
    )
    assert f"CORS_ORIGINS={ORIGENES_CLASE}" in lineas


def _ejecutar_sondeo_middleware() -> dict:
    """Importa app.py con CORS_ORIGINS controlado y sondea con TestClient."""
    entorno = os.environ.copy()
    entorno["CORS_ORIGINS"] = "http://localhost:3000"

    codigo = """
import json
import sys
import types

dotenv = types.ModuleType("dotenv")
dotenv.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv

from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from app import app

cliente = TestClient(app)
origen_permitido = "http://localhost:3000"

def resumir(respuesta):
    return {
        "status": respuesta.status_code,
        "headers": {k.lower(): v for k, v in respuesta.headers.items()},
    }

def preflight(ruta, metodo, cabeceras="content-type"):
    return cliente.options(
        ruta,
        headers={
            "Origin": origen_permitido,
            "Access-Control-Request-Method": metodo,
            "Access-Control-Request-Headers": cabeceras,
        },
    )

middleware = next(
    (elemento for elemento in app.user_middleware if elemento.cls is CORSMiddleware),
    None,
)
rutas = {
    "health": ("/health", "GET"),
    "ask": ("/ask", "POST"),
    "approve": ("/approve", "POST"),
    "messages": ("/threads/hilo-test/messages", "GET"),
}
preflights = {
    nombre: resumir(preflight(ruta, metodo))
    for nombre, (ruta, metodo) in rutas.items()
}

resultado = {
    "middleware": None if middleware is None else middleware.kwargs,
    "health_permitido": resumir(
        cliente.get("/health", headers={"Origin": origen_permitido})
    ),
    "health_no_permitido": resumir(
        cliente.get("/health", headers={"Origin": "https://no-permitido.test"})
    ),
    "preflights": preflights,
    "metodo_no_permitido": resumir(preflight("/health", "DELETE", "")),
    "cabecera_no_permitida": resumir(preflight("/ask", "POST", "x-prueba")),
}
print(json.dumps(resultado))
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


def test_middleware_cors_configurado():
    middleware = _ejecutar_sondeo_middleware()["middleware"]

    assert middleware is not None
    assert middleware["allow_origins"] == ["http://localhost:3000"]
    assert middleware["allow_credentials"] is False
    assert middleware["allow_methods"] == ["GET", "POST"]
    assert middleware["allow_headers"] == ["Accept", "Content-Type"]


def test_preflight_permitido_devuelve_cabeceras_cors():
    resultado = _ejecutar_sondeo_middleware()
    respuesta = resultado["preflights"]["ask"]

    assert respuesta["status"] == 200
    assert respuesta["headers"]["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in respuesta["headers"]["access-control-allow-methods"]
    assert "content-type" in respuesta["headers"]["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in respuesta["headers"]


def test_origen_no_permitido_no_recibe_cabecera_cors():
    respuesta = _ejecutar_sondeo_middleware()["health_no_permitido"]

    assert respuesta["status"] == 200
    assert "access-control-allow-origin" not in respuesta["headers"]


def test_preflight_cors_en_rutas_de_api():
    preflights = _ejecutar_sondeo_middleware()["preflights"]

    assert set(preflights) == {"health", "ask", "approve", "messages"}
    for respuesta in preflights.values():
        assert respuesta["status"] == 200
        assert respuesta["headers"]["access-control-allow-origin"] == "http://localhost:3000"


def test_preflight_rechaza_metodo_y_cabecera_no_permitidos():
    resultado = _ejecutar_sondeo_middleware()

    assert resultado["metodo_no_permitido"]["status"] == 400
    assert resultado["cabecera_no_permitida"]["status"] == 400


def test_readme_documenta_cors_local_y_render():
    texto = (RAIZ / "README.md").read_text(encoding="utf-8")
    texto_minusculas = texto.lower()

    assert "cors_origins" in texto_minusculas
    assert ORIGENES_CLASE in texto
    assert "separados por comas" in texto_minusculas
    assert ".env" in texto
    assert "servicio de la api en render" in texto_minusculas
