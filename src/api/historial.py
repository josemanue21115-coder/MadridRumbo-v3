"""Adaptador del historial persistido y contexto temporal de la API (SPEC-016)."""
from dataclasses import dataclass, field

from sqlmodel import Session

from src.api.esquemas import MessageOut
from src.history import get_thread_messages
from src.models import Conversation


@dataclass
class RegistroTemporal:
    """Hilos y preguntas del proceso actual; no sustituye al checkpoint del agente."""

    _hilos: set[str] = field(default_factory=set)
    _preguntas: dict[str, str] = field(default_factory=dict)

    def registrar_hilo(self, thread_id: str) -> None:
        self._hilos.add(thread_id)

    def conoce_hilo(self, thread_id: str) -> bool:
        return thread_id in self._hilos

    def guardar_pregunta(self, thread_id: str, pregunta: str) -> None:
        """Conserva la primera pregunta hasta que su turno termine explícitamente."""
        self.registrar_hilo(thread_id)
        self._preguntas.setdefault(thread_id, pregunta)

    def obtener_pregunta(self, thread_id: str) -> str | None:
        return self._preguntas.get(thread_id)

    def finalizar_turno(self, thread_id: str) -> None:
        """Libera la pregunta, manteniendo el hilo conocido durante este proceso."""
        self._preguntas.pop(thread_id, None)

    def limpiar(self) -> None:
        self._preguntas.clear()
        self._hilos.clear()


# Se sustituye por una instancia nueva en cada caso de prueba de la API.
registro_temporal = RegistroTemporal()


def es_hilo_conocido(session: Session, thread_id: str) -> bool:
    """Reconoce datos persistidos o un hilo temporal sin insertar filas al consultar."""
    return session.get(Conversation, thread_id) is not None or registro_temporal.conoce_hilo(thread_id)


def leer_historial(session: Session, thread_id: str) -> list[MessageOut]:
    """Enumera por hilo los mensajes que SPEC-014 ya recupera ordenados por id."""
    return [
        MessageOut(role=mensaje.role, content=mensaje.content, orden=orden)
        for orden, mensaje in enumerate(get_thread_messages(session, thread_id), start=1)
    ]
