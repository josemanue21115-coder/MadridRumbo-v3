"""API REST del agente MadridRumbo (spec 013).

Expone como servicio HTTP el mismo agente que usan la terminal y la web.
Se arranca con: uvicorn app:app
La documentación interactiva queda disponible en /docs.
"""
import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

import config
import src.db as db
from src.api import historial, servicio
from src.api.esquemas import ApproveIn, AskIn, AskOut, MessageOut, ThreadId
from src.api.logs_peticion import RegistroPeticionesProtegidas
from src.api.seguridad import validar_api_key


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Prepara persistencia antes de servir y libera el contexto local al terminar."""
    historial.registro_temporal.limpiar()
    servicio._planes_pendientes.clear()
    servicio._agente = None
    try:
        db.create_db_and_tables()
        motor = db.get_engine()
    except Exception:
        raise RuntimeError(config.API_ERROR_ARRANQUE_DB) from None
    try:
        yield
    finally:
        historial.registro_temporal.limpiar()
        servicio._planes_pendientes.clear()
        servicio._agente = None
        motor.dispose()


app = FastAPI(
    title="MadridRumbo API - TEST Environment",
    description="Asistente de transporte público de Madrid: preguntas al agente y aprobación de planes.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS permite a los navegadores usar la API desde los orígenes configurados.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type"],
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
    """Sanea las queries y suprime access logs duplicados de rutas protegidas."""

    def filter(self, record: logging.LogRecord) -> bool:
        argumentos = record.args
        if isinstance(argumentos, tuple) and len(argumentos) >= 3:
            ruta = argumentos[2]
            if isinstance(ruta, str):
                metodo = argumentos[1]
                ruta_sin_query = ruta.partition("?")[0]
                argumentos_saneados = list(argumentos)
                argumentos_saneados[2] = ruta_sin_query
                record.args = tuple(argumentos_saneados)
                es_protegida = (
                    metodo == "POST" and ruta_sin_query in {"/ask", "/approve"}
                ) or (
                    metodo == "GET"
                    and re.fullmatch(r"/threads/[^/]+/messages", ruta_sin_query)
                    is not None
                )
                if es_protegida:
                    return False
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
async def ask(
    datos: AskIn,
    request: Request,
    session: Session = Depends(db.get_session),
    _autenticacion: None = Depends(validar_api_key),
) -> AskOut:
    """Envía una pregunta al agente y devuelve su respuesta.

    Si no se indica `thread_id`, se crea una conversación nueva. Una pregunta vacía da error 422.
    Con `auto_aprobar` activo, un plan único se aprueba solo; con varios planes, se devuelven pendientes.
    """
    request.state.thread_id = datos.thread_id
    try:
        resultado = await asyncio.wait_for(
            asyncio.to_thread(servicio.preguntar, datos, session),
            timeout=config.ASK_TIMEOUT_SECONDS,
        )
        request.state.thread_id = resultado.thread_id
        return resultado
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=MENSAJE_TIMEOUT_ASK) from None


@app.post("/approve", response_model=AskOut, tags=["Agente"], responses=ERROR_500)
def approve(
    datos: ApproveIn,
    request: Request,
    session: Session = Depends(db.get_session),
    _autenticacion: None = Depends(validar_api_key),
) -> AskOut:
    """Aprueba o rechaza el plan pendiente de una conversación.

    `plan_id` solo es necesario cuando hay varios planes pendientes.
    Si no hay plan pendiente, el aviso llega en el campo `error`.
    """
    request.state.thread_id = datos.thread_id
    return servicio.aprobar(datos, session)


@app.get(
    "/threads/{thread_id}/messages",
    response_model=list[MessageOut],
    tags=["Historial"],
    responses={404: {"description": "Conversación no encontrada."}, **ERROR_500},
)
def messages(
    thread_id: ThreadId,
    session: Session = Depends(db.get_session),
    _autenticacion: None = Depends(validar_api_key),
) -> list[MessageOut]:
    """Recupera el historial finalizado, ordenado dentro de la conversación."""
    return servicio.obtener_historial(session, thread_id)


# Se envuelve por fuera de FastAPI para observar también las respuestas de error globales.
app = RegistroPeticionesProtegidas(app)
