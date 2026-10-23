"""In-memory hybrid index. Tests and the ranker use this. Postgres is the app index."""

from __future__ import annotations

from app.rag.embed import Embedder, MiniLMEmbedder
from app.rag.rank import bm25_ranking, reciprocal_rank_fusion, vector_ranking
from app.rag.text import shares_support
from app.rag.types import Hit, RawChunk, StoredChunk, chunk_id


class MemoryHybridIndex:
    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder or MiniLMEmbedder()
        self._chunks: list[StoredChunk] = []

    def replace(self, chunks: list[RawChunk]) -> None:
        if not chunks:
            self._chunks = []
            return
        vectors = self._embedder.embed([chunk.content for chunk in chunks])
        self._chunks = [
            StoredChunk(
                source=chunk.source,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=tuple(vector),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]

    def search(self, query: str, *, limit: int) -> list[Hit]:
        cleaned = query.strip()
        if not cleaned or not self._chunks or limit < 1:
            return []
        query_vector = self._embedder.embed([cleaned])[0]
        fused = reciprocal_rank_fusion(
            [
                vector_ranking(query_vector, self._chunks, limit=limit),
                bm25_ranking(cleaned, self._chunks, limit=limit),
            ]
        )
        by_id = {chunk_id(chunk.source, chunk.chunk_index): chunk for chunk in self._chunks}
        hits: list[Hit] = []
        for cid, score in fused:
            if len(hits) >= limit:
                break
            chunk = by_id[cid]
            if not shares_support(cleaned, chunk.content):
                continue
            hits.append(
                Hit(
                    source=chunk.source,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=score,
                )
            )
        return hits
