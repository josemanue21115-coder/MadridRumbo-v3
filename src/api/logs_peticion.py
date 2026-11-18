"""Registro de campos operativos de las peticiones protegidas de la API."""
import json
import logging
import re
from time import perf_counter
from typing import Any


_logger = logging.getLogger(__name__)
_RUTA_HISTORIAL = re.compile(r"^/threads/([^/]+)/messages$")


def _es_ruta_protegida(metodo: str, ruta: str) -> bool:
    """Reconoce las rutas protegidas sin consultar ni registrar la query."""
    if metodo == "POST" and ruta in {"/ask", "/approve"}:
        return True
    return metodo == "GET" and _RUTA_HISTORIAL.fullmatch(ruta) is not None


class RegistroPeticionesProtegidas:
    """Envoltorio ASGI exterior que registra una vez cada petición protegida."""

    def __init__(self, aplicacion: Any):
        self.aplicacion = aplicacion

    def __getattr__(self, nombre: str) -> Any:
        """Conserva disponibles los atributos FastAPI usados por herramientas y tests."""
        return getattr(self.aplicacion, nombre)

    async def __call__(self, scope: dict, receive, send) -> None:
        if scope.get("type") != "http":
            await self.aplicacion(scope, receive, send)
            return

        metodo = scope.get("method", "")
        ruta = scope.get("path", "")
        coincidencia_historial = _RUTA_HISTORIAL.fullmatch(ruta)
        if not _es_ruta_protegida(metodo, ruta):
            await self.aplicacion(scope, receive, send)
            return

        inicio = perf_counter()
        estado_http = None

        async def enviar_con_estado(mensaje: dict) -> None:
            nonlocal estado_http
            if mensaje.get("type") == "http.response.start":
                estado_http = mensaje.get("status")
            await send(mensaje)

        try:
            await self.aplicacion(scope, receive, enviar_con_estado)
        finally:
            estado = scope.get("state") or {}
            thread_id = estado.get("thread_id")
            if coincidencia_historial:
                thread_id = coincidencia_historial.group(1)

            evento = {
                "event": "protected_request",
                "method": metodo,
                "route": ruta,
                "thread_id": thread_id,
                "duration_ms": round((perf_counter() - inicio) * 1000, 3),
                "status_code": estado_http,
            }
            _logger.info(json.dumps(evento, ensure_ascii=False, separators=(",", ":")))
