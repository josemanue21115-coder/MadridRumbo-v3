"""Tests de las rutas básicas de la API (spec 013, RF-2, RF-3 y RF-16).

Se usa el cliente de pruebas de FastAPI: llama a la API sin arrancar ningún servidor
ni hacer peticiones reales, así que no gasta API.
"""

import config


def test_health_responde_ok(cliente_api):
    # El servicio indica que está vivo (RF-3).
    respuesta = cliente_api.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


def test_health_indica_modo_simulado(cliente_api, monkeypatch):
    # Con la variable de entorno del modo simulado, /health lo anuncia (RF-16).
    monkeypatch.setenv(config.VARIABLE_MODO_SIMULADO, config.VALOR_MODO_SIMULADO)
    assert cliente_api.get("/health").json()["modo"] == "simulado"


def test_health_indica_modo_real(cliente_api, monkeypatch):
    # Sin esa variable, el servicio funciona con el agente real.
    monkeypatch.delenv(config.VARIABLE_MODO_SIMULADO, raising=False)
    assert cliente_api.get("/health").json()["modo"] == "real"


def test_docs_son_publicas(cliente_api):
    # La documentación interactiva abre sin clave de acceso (RF-2).
    assert cliente_api.get("/docs").status_code == 200


def test_esquema_incluye_health(cliente_api):
    # El esquema que alimenta /docs describe la ruta /health.
    esquema = cliente_api.get("/openapi.json").json()
    assert "/health" in esquema["paths"]
