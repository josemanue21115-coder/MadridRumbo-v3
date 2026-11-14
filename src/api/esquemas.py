"""Formatos de datos de la API (spec 013): lo que entra y sale por cada ruta.

Cada clase es un "formulario". Pydantic comprueba que los datos que llegan cumplen
sus reglas y, si no, FastAPI responde solo con un error 422 sin llegar al agente.
Estas clases también alimentan la documentación interactiva de /docs.
"""
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AskIn(BaseModel):
    """Pregunta que llega a POST /ask."""

    pregunta: str = Field(description="Pregunta de la persona usuaria.")
    # Opcional: si no llega, la API crea una conversación nueva (RF-6).
    thread_id: str | None = Field(
        default=None,
        description="Identificador de la conversación. Si falta, se crea uno nuevo.",
    )
    # Activada por defecto porque facilita probar desde /docs sin pasar por el paso de aprobación.
    auto_aprobar: bool = Field(
        default=True,
        description="Si es verdadero y hay un único plan pendiente, se aprueba solo.",
    )

    @field_validator("pregunta")
    @classmethod
    def pregunta_no_vacia(cls, valor: str) -> str:
        # Una pregunta de solo espacios no debe llegar al agente (RF-5).
        if not valor.strip():
            raise ValueError("La pregunta no puede estar vacía.")
        return valor


class AskOut(BaseModel):
    """Resultado de un turno; lo devuelven POST /ask y POST /approve con el mismo formato."""

    respuesta: str
    thread_id: str
    # `done` y `pendiente_hitl` los decide siempre el agente; la API solo los traslada (RF-15).
    done: bool
    pendiente_hitl: bool
    # Planes pendientes de aprobar: la web los necesita para mostrarlos antes de decidir.
    plan: list[Any] = Field(default_factory=list)
    # Mensaje de aviso cuando el agente rechaza la petición (por ejemplo, aprobar sin plan pendiente).
    error: str | None = None


class ApproveIn(BaseModel):
    """Decisión sobre un plan pendiente, para POST /approve."""

    thread_id: str = Field(min_length=1)
    # Verdadero aprueba el plan; falso lo rechaza y la conversación continúa (RF-12).
    aprobado: bool
    # El agente puede devolver varios planes a la vez; entonces hay que indicar cuál se decide (RF-11).
    plan_id: str | None = Field(
        default=None,
        description="Solo hace falta cuando hay varios planes pendientes.",
    )


class MessageOut(BaseModel):
    """Un mensaje del historial. Lo rellena la spec de la base de datos; aquí solo se declara el formato."""

    role: str
    content: str
    orden: int