"""SQLAlchemy database engine and session lifecycle helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _ensure_sqlite_dir(database_url: str) -> None:
    if database_url.startswith("sqlite:///") and ":memory:" not in database_url:
        raw_path = database_url.replace("sqlite:///", "", 1)
        # On Unix/Vercel sqlite:////tmp/... leaves a leading slash
        path = Path(raw_path)
        if path.parent and str(path.parent) not in ("", "."):
            path.parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    # Normalize legacy postgres:// scheme used by some cloud providers (Neon/Supabase/Heroku)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    _ensure_sqlite_dir(url)

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        future=True,
    )

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            if ":memory:" not in url:
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine: Engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db(target_engine: Engine | None = None) -> None:
    """Create all database tables if they do not exist."""
    from app.db import models  # noqa: F401  # ensure models are registered

    Base.metadata.create_all(bind=target_engine or engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
