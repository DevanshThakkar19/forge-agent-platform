"""Shared API test fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.mcp.client import InProcessToolClient
from app.rag.corpus import load_chunks
from app.rag.memory import MemoryHybridIndex
from app.rag.retrieve import HybridRetriever

CORPUS_DIR = Path(__file__).resolve().parents[1] / "corpus"


class StaticProbe:
    def __init__(self, ok: bool) -> None:
        self._ok = ok

    def ping(self) -> bool:
        return self._ok


def memory_retriever(limit: int = 4) -> HybridRetriever:
    index = MemoryHybridIndex()
    index.replace(load_chunks(CORPUS_DIR))
    return HybridRetriever(index, limit=limit)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        corpus_dir=CORPUS_DIR,
        tool_transport="inprocess",
        planner="keyword",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    application = create_app(
        settings,
        client=InProcessToolClient(settings.sandbox_root),
        retriever=memory_retriever(),
        database_probe=StaticProbe(False),
    )
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def auth_header() -> dict[str, str]:
    return {"X-API-Key": "test-key"}
