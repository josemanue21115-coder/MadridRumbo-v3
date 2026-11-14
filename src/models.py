"""Modelos de historial persistente de conversaciones."""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    thread_id: str = Field(primary_key=True, max_length=128)
    created_at: datetime = Field(default_factory=utc_now)


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: str = Field(foreign_key="conversations.thread_id", index=True)
    role: str = Field(max_length=20)
    content: str
    created_at: datetime = Field(default_factory=utc_now)
