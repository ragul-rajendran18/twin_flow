"""SQLAlchemy engine, session factory and FastAPI session dependency."""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _build_engine(url: str) -> Engine:
    kwargs: dict = {"future": True, "echo": settings.db_echo, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = _build_engine(settings.sync_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def check_database_connection() -> bool:
    """Return True when the database is reachable (never raises)."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.warning("Database connectivity check failed: %s", exc.__class__.__name__)
        return False


def get_db():
    """FastAPI dependency yielding a session; always closed, rolled back on error."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


__all__ = ["Base", "engine", "SessionLocal", "get_db", "check_database_connection"]
