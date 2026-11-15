"""API REST del agente MadridRumbo (spec 013).

Expone como servicio HTTP el mismo agente que usan la terminal y la web.
Se arranca con: uvicorn app:app
La documentación interactiva queda disponible en /docs.
"""
import os

from fastapi import Depends, FastAPI
from sqlmodel import Session

import config
import src.db as db
from src.api import servicio
from src.api.esquemas import ApproveIn, AskIn, AskOut, MessageOut, ThreadId

app = FastAPI(
    title="MadridRumbo API",
    description="Asistente de transporte público de Madrid: preguntas al agente y aprobación de planes.",
    version="1.0.0",
)

# Respuesta documentada para los fallos inesperados del agente.
ERROR_500 = {500: {"description": "Fallo inesperado al procesar la consulta."}}


def _modo_agente() -> str:
    # El modo simulado se activa con una variable de entorno y permite probar sin gastar API.
    simulado = os.environ.get(config.VARIABLE_MODO_SIMULADO) == config.VALOR_MODO_SIMULADO
    return "simulado" if simulado else "real"


@app.get("/health", tags=["Estado"])
def health() -> dict:
    """Comprueba que el servicio está vivo e indica si usa el agente real o el simulado."""
    return {"estado": "ok", "modo": _modo_agente()}


@app.post("/ask", response_model=AskOut, tags=["Agente"], responses=ERROR_500)
def ask(datos: AskIn) -> AskOut:
    """Envía una pregunta al agente y devuelve su respuesta.

    Si no se indica `thread_id`, se crea una conversación nueva. Una pregunta vacía da error 422.
    Con `auto_aprobar` activo, un plan único se aprueba solo; con varios planes, se devuelven pendientes.
    """
    return servicio.preguntar(datos)


@app.post("/approve", response_model=AskOut, tags=["Agente"], responses=ERROR_500)
def approve(datos: ApproveIn) -> AskOut:
    """Aprueba o rechaza el plan pendiente de una conversación.

    `plan_id` solo es necesario cuando hay varios planes pendientes.
    Si no hay plan pendiente, el aviso llega en el campo `error`.
    """
    return servicio.aprobar(datos)


@app.get(
    "/threads/{thread_id}/messages",
    response_model=list[MessageOut],
    tags=["Historial"],
    responses={404: {"description": "Conversación no encontrada."}, **ERROR_500},
)
def messages(thread_id: ThreadId, session: Session = Depends(db.get_session)) -> list[MessageOut]:
    """Recupera el historial finalizado, ordenado dentro de la conversación."""
    return servicio.obtener_historial(session, thread_id)
