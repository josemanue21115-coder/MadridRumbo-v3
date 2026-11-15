"""SPEC-016: el lifespan exige preparar PostgreSQL antes de servir la API."""
import pytest
from fastapi.testclient import TestClient

import src.db as db
from app import app
from src.api import historial, servicio


def test_arranque_prepara_tablas_y_limpia_estado(entorno_api, monkeypatch):
    llamadas = []
    preparar = db.create_db_and_tables
    def contar():
        llamadas.append("preparar")
        preparar()
    monkeypatch.setattr(db, "create_db_and_tables", contar)
    historial.registro_temporal.guardar_pregunta("anterior", "No debe heredarse")
    with TestClient(app) as cliente:
        assert llamadas == ["preparar"]
        assert not historial.registro_temporal.conoce_hilo("anterior")
        assert cliente.get("/health").status_code == 200
        respuesta = cliente.post("/ask", json={"pregunta": "Ruta de Sol a Atocha", "auto_aprobar": False})
        hilo = respuesta.json()["thread_id"]
        assert historial.registro_temporal.conoce_hilo(hilo)
    assert not historial.registro_temporal.conoce_hilo(hilo)
    assert servicio._planes_pendientes == {}
    assert servicio._agente is None


@pytest.mark.parametrize("causa", ["configuracion", "conexion", "tablas"])
def test_arranque_postgresql_obligatorio(entorno_api, monkeypatch, causa):
    def fallar():
        if causa == "configuracion":
            raise ValueError("DATABASE_URL no configurada")
        if causa == "conexion":
            raise ConnectionError("credencial ficticia que no debe salir")
        raise RuntimeError("DDL fallido")
    monkeypatch.setattr(db, "create_db_and_tables", fallar)
    with pytest.raises(RuntimeError, match="No se pudo preparar la persistencia"):
        with TestClient(app):
            pytest.fail("La API no debe servir con un arranque fallido")
