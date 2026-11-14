"""Historial PB3 separado del checkpoint MemorySaver de LangGraph."""
from sqlmodel import Session, select

from .models import Conversation, Message


def save_closed_turn(session: Session, thread_id: str, question: str, answer: str) -> None:
    """Persiste solo tras el cierre real del turno; la API decide cuándo cerrar."""
    if not isinstance(thread_id, str) or not thread_id.strip() or len(thread_id) > 128:
        raise ValueError("thread_id debe tener entre 1 y 128 caracteres")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question debe ser texto no vacío")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("answer debe ser texto no vacío")
    try:
        if session.get(Conversation, thread_id) is None:
            session.add(Conversation(thread_id=thread_id))
            session.flush()
        session.add(Message(thread_id=thread_id, role="user", content=question))
        session.add(Message(thread_id=thread_id, role="assistant", content=answer))
        session.commit()
    except Exception:
        session.rollback()
        raise


def get_thread_messages(session: Session, thread_id: str) -> list[Message]:
    """Devuelve los mensajes en orden estable de inserción."""
    return list(
        session.exec(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.id)
        ).all()
    )
