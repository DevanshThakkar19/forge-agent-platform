"""pgvector storage. Cosine and full-text search run in Postgres. Fusion does not."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from app.rag.embed import EMBED_DIM, Embedder, MiniLMEmbedder
from app.rag.rank import VECTOR_MIN_COSINE, reciprocal_rank_fusion
from app.rag.text import shares_support
from app.rag.types import Hit, RawChunk, chunk_id

_SCHEMA = re.compile(r"^[a-z_][a-z0-9_]*$")


class DatabaseProbe(Protocol):
    def ping(self) -> bool:
        """Return whether Postgres accepts a connection."""


class PgDatabaseProbe:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def ping(self) -> bool:
        return ping_database(self._database_url)


def ping_database(database_url: str, *, timeout_s: int = 2) -> bool:
    try:
        with psycopg.connect(database_url, connect_timeout=timeout_s) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


class PgHybridIndex:
    def __init__(
        self,
        database_url: str,
        embedder: Embedder | None = None,
        *,
        schema: str = "public",
        connect_timeout_s: int = 2,
    ) -> None:
        if not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid schema name")
        self._database_url = database_url
        self._embedder = embedder or MiniLMEmbedder()
        self._schema = schema
        self._timeout = connect_timeout_s
        self._chunks = f"{schema}.forge_chunks"
        self._meta = f"{schema}.forge_index_meta"

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            if self._schema != "public":
                conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self._schema}")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._chunks} (
                    source text NOT NULL,
                    chunk_index int NOT NULL,
                    content text NOT NULL,
                    embedding vector({EMBED_DIM}) NOT NULL,
                    PRIMARY KEY (source, chunk_index)
                )
                """
            )
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._meta} (
                    id int PRIMARY KEY,
                    corpus_sha256 text NOT NULL
                )
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS forge_chunks_embedding_hnsw
                ON {self._chunks} USING hnsw (embedding vector_cosine_ops)
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS forge_chunks_fts
                ON {self._chunks} USING gin (to_tsvector('english', content))
                """
            )

    def current_fingerprint(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute(f"SELECT corpus_sha256 FROM {self._meta} WHERE id = 1").fetchone()
        if row is None:
            return None
        return str(row[0])

    def replace(self, chunks: list[RawChunk], fingerprint: str) -> None:
        vectors = self._embedder.embed([chunk.content for chunk in chunks]) if chunks else []
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {self._chunks}")
            for chunk, vector in zip(chunks, vectors, strict=True):
                conn.execute(
                    f"""
                    INSERT INTO {self._chunks} (source, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (chunk.source, chunk.chunk_index, chunk.content, Vector(vector)),
                )
            conn.execute(f"DELETE FROM {self._meta}")
            conn.execute(
                f"INSERT INTO {self._meta} (id, corpus_sha256) VALUES (1, %s)",
                (fingerprint,),
            )

    def search(self, query: str, *, limit: int) -> list[Hit]:
        cleaned = query.strip()
        if not cleaned or limit < 1:
            return []
        query_vector = Vector(self._embedder.embed([cleaned])[0])
        with self._connect() as conn:
            vector_rows = conn.execute(
                f"""
                SELECT source, chunk_index, content
                FROM {self._chunks}
                WHERE 1 - (embedding <=> %s) >= %s
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (query_vector, VECTOR_MIN_COSINE, query_vector, limit),
            ).fetchall()
            keyword_rows = conn.execute(
                f"""
                SELECT source, chunk_index, content
                FROM {self._chunks}
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                ORDER BY ts_rank(
                    to_tsvector('english', content),
                    plainto_tsquery('english', %s)
                ) DESC, source, chunk_index
                LIMIT %s
                """,
                (cleaned, cleaned, limit),
            ).fetchall()

        by_id: dict[str, tuple[str, int, str]] = {}
        vector_ids: list[str] = []
        for source, index, content in vector_rows:
            cid = chunk_id(str(source), int(index))
            by_id[cid] = (str(source), int(index), str(content))
            vector_ids.append(cid)
        keyword_ids: list[str] = []
        for source, index, content in keyword_rows:
            cid = chunk_id(str(source), int(index))
            by_id[cid] = (str(source), int(index), str(content))
            keyword_ids.append(cid)

        hits: list[Hit] = []
        for cid, score in reciprocal_rank_fusion([vector_ids, keyword_ids]):
            if len(hits) >= limit:
                break
            source, index, content = by_id[cid]
            if not shares_support(cleaned, content):
                continue
            hits.append(Hit(source=source, chunk_index=index, content=content, score=score))
        return hits

    @contextmanager
    def _connect(self) -> Iterator[psycopg.Connection]:
        conn = psycopg.connect(self._database_url, connect_timeout=self._timeout)
        try:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(conn)
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
