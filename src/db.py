"""Persistencia PB3: se integra con config.py de MadridRumbo."""
from functools import lru_cache

from sqlmodel import Session, SQLModel, create_engine

import config
from . import models  # registra las tablas antes de create_all


def normalize_database_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("DATABASE_URL no está configurada")
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


@lru_cache(maxsize=1)
def get_engine():
    url = normalize_database_url(config.DATABASE_URL)
    if not (url.startswith("postgresql://") or url.startswith("postgresql+psycopg://")):
        raise ValueError("Se requiere PostgreSQL en desarrollo y producción")
    return create_engine(url, pool_pre_ping=True)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session():
    with Session(get_engine()) as session:
        yield session
