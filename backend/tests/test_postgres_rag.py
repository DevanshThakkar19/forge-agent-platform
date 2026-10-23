"""pgvector hybrid search. Skips when Postgres is down unless CI requires it."""

from __future__ import annotations

import os

import psycopg
import pytest
from tests.conftest import CORPUS_DIR

from app.rag.corpus import corpus_fingerprint, load_chunks
from app.rag.postgres import PgHybridIndex

_SCHEMA = "forge_rag_test"


def _database_url() -> str:
    return os.environ.get(
        "FORGE_DATABASE_URL",
        "postgresql://forge:forge@localhost:5432/forge",
    )


@pytest.fixture
def pg_index() -> PgHybridIndex:
    url = _database_url()
    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
    except Exception:
        if os.environ.get("FORGE_REQUIRE_DATABASE") == "1":
            pytest.fail("postgres is required but unavailable")
        pytest.skip("postgres unavailable")
    index = PgHybridIndex(url, schema=_SCHEMA)
    index.ensure_schema()
    index.replace(load_chunks(CORPUS_DIR), corpus_fingerprint(CORPUS_DIR))
    try:
        yield index
    finally:
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE")
            conn.commit()


def test_pgvector_search_ranks_the_orders_chunk(pg_index: PgHybridIndex) -> None:
    hits = pg_index.search("shipped order 1001", limit=3)
    assert hits
    assert hits[0].source == "corpus/orders.md"
    assert pg_index.search("banana milkshake", limit=3) == []
