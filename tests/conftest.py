"""Pytest fixtures for isolated database, FastAPI TestClient, and mocked AI services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncGenerator, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, create_db_engine, get_db
from app.main import create_app


@dataclass
class FakeChunk:
    content: str


class FakeStreamingLLM:
    """Deterministic async streaming LLM double for tests."""

    def __init__(self, tokens: List[str]) -> None:
        self.tokens = tokens
        self.received_messages: List[list] = []

    async def astream(self, messages) -> AsyncGenerator[FakeChunk, None]:
        self.received_messages.append(list(messages))
        for tok in self.tokens:
            yield FakeChunk(content=tok)

    async def ainvoke(self, messages) -> FakeChunk:
        self.received_messages.append(list(messages))
        return FakeChunk(content="".join(self.tokens))


@pytest.fixture()
def client(tmp_path):
    db_file = tmp_path / "test_chat.db"
    engine = create_db_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
    )

    app = create_app()

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()
