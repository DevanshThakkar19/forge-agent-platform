"""Retriever seam used by the worker. The index can be memory or Postgres."""

from __future__ import annotations

import logging
from typing import Protocol

from app.rag.types import Hit

logger = logging.getLogger("forge.rag")


class SearchIndex(Protocol):
    def search(self, query: str, *, limit: int) -> list[Hit]:
        """Return fused hits, best first."""


class Retriever(Protocol):
    def retrieve(self, query: str) -> dict:
        """Return ok, citations, and optional error. Do not raise for an empty index."""


class HybridRetriever:
    def __init__(self, index: SearchIndex, *, limit: int = 4) -> None:
        self._index = index
        self._limit = limit

    def retrieve(self, query: str) -> dict:
        try:
            hits = self._index.search(query, limit=self._limit)
        except Exception:
            logger.exception("retrieval failed")
            return {"ok": False, "error": "retrieval failed", "citations": []}
        citations = []
        matches = []
        for hit in hits:
            cited = _cite(hit.source, hit.content)
            if cited is None:
                continue
            citations.append(cited)
            matches.append({"source": hit.source, "score": round(hit.score, 6)})
        return {"ok": True, "citations": citations, "matches": matches}


class UnavailableRetriever:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def retrieve(self, query: str) -> dict:
        return {"ok": False, "error": self._reason, "citations": []}


def _cite(source: str, excerpt: str) -> dict[str, str] | None:
    cleaned_source = source.strip()[:200]
    cleaned_excerpt = excerpt.strip()[:240]
    if not cleaned_source or not cleaned_excerpt:
        return None
    return {"source": cleaned_source, "excerpt": cleaned_excerpt}
