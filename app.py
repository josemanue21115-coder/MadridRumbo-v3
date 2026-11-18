"""API REST del agente MadridRumbo (spec 013).

Expone como servicio HTTP el mismo agente que usan la terminal y la web.
Se arranca con: uvicorn app:app
La documentación interactiva queda disponible en /docs.
"""
import asyncio
import logging
import os

from fastapi import Depends, FastAPI, HTTPException

import config
from src.api import servicio
from src.api.esquemas import ApproveIn, AskIn, AskOut, MessageOut
from src.api.seguridad import validar_api_key

app = FastAPI(
    title="MadridRumbo API",
    description="Asistente de transporte público de Madrid: preguntas al agente y aprobación de planes.",
    version="1.0.0",
)

# Respuesta documentada para los fallos inesperados del agente.
ERROR_500 = {500: {"description": "Fallo inesperado al procesar la consulta."}}
ERROR_ASK = {
    **ERROR_500,
    504: {"description": "El turno de /ask ha superado el tiempo máximo permitido."},
}
MENSAJE_TIMEOUT_ASK = "El turno ha superado el tiempo máximo permitido. Inténtalo de nuevo."
logger = logging.getLogger(__name__)


class _FiltroAccessLog(logging.Filter):
    """Elimina la query de la ruta antes de que Uvicorn formatee el access log."""

    def filter(self, record: logging.LogRecord) -> bool:
        argumentos = record.args
        if isinstance(argumentos, tuple) and len(argumentos) >= 3:
            ruta = argumentos[2]
            if isinstance(ruta, str):
                argumentos_saneados = list(argumentos)
                argumentos_saneados[2] = ruta.partition("?")[0]
                record.args = tuple(argumentos_saneados)
        return True


_logger_access = logging.getLogger("uvicorn.access")
if not any(isinstance(filtro, _FiltroAccessLog) for filtro in _logger_access.filters):
    _logger_access.addFilter(_FiltroAccessLog())


def _modo_agente() -> str:
    # El modo simulado se activa con una variable de entorno y permite probar sin gastar API.
    simulado = os.environ.get(config.VARIABLE_MODO_SIMULADO) == config.VALOR_MODO_SIMULADO
    return "simulado" if simulado else "real"


@app.get("/health", tags=["Estado"])
def health() -> dict:
    """Comprueba que el servicio está vivo e indica si usa el agente real o el simulado."""
    return {"estado": "ok", "modo": _modo_agente()}


@app.post("/ask", response_model=AskOut, tags=["Agente"], responses=ERROR_ASK)
async def ask(datos: AskIn, _autenticacion: None = Depends(validar_api_key)) -> AskOut:
    """Envía una pregunta al agente y devuelve su respuesta.

    Si no se indica `thread_id`, se crea una conversación nueva. Una pregunta vacía da error 422.
    Con `auto_aprobar` activo, un plan único se aprueba solo; con varios planes, se devuelven pendientes.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(servicio.preguntar, datos),
            timeout=config.ASK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("Timeout al procesar el turno de /ask.")
        raise HTTPException(status_code=504, detail=MENSAJE_TIMEOUT_ASK) from None


@app.post("/approve", response_model=AskOut, tags=["Agente"], responses=ERROR_500)
def approve(datos: ApproveIn, _autenticacion: None = Depends(validar_api_key)) -> AskOut:
    """Aprueba o rechaza el plan pendiente de una conversación.

    `plan_id` solo es necesario cuando hay varios planes pendientes.
    Si no hay plan pendiente, el aviso llega en el campo `error`.
    """
    return servicio.aprobar(datos)


@app.get(
    "/threads/{thread_id}/messages",
    response_model=list[MessageOut],
    tags=["Historial"],
    responses={501: {"description": "Todavía no implementada: depende del historial en base de datos."}},
)
def messages(
    thread_id: str, _autenticacion: None = Depends(validar_api_key)
) -> list[MessageOut]:
    """Devuelve los mensajes de una conversación (role, content, orden).

    Ruta reservada: la implementa quien se encarga de la base de datos.
    """
    raise HTTPException(status_code=501, detail=config.API_MENSAJES_NO_IMPLEMENTADO)
