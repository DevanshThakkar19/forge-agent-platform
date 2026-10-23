"""Build the Postgres retriever and ingest the corpus when the fingerprint changes."""

from __future__ import annotations

import logging
from pathlib import Path

from app.rag.corpus import corpus_fingerprint, load_chunks
from app.rag.embed import EMBEDDER_ID, HashingEmbedder
from app.rag.postgres import PgHybridIndex
from app.rag.retrieve import HybridRetriever, Retriever, UnavailableRetriever

logger = logging.getLogger("forge.rag")


def build_retriever(database_url: str, corpus_dir: Path, *, limit: int) -> Retriever:
    try:
        index = PgHybridIndex(database_url, HashingEmbedder())
        index.ensure_schema()
        _sync_corpus(index, corpus_dir)
    except Exception:
        logger.exception("rag index unavailable")
        return UnavailableRetriever("database unavailable")
    return HybridRetriever(index, limit=limit)


def _sync_corpus(index: PgHybridIndex, corpus_dir: Path) -> None:
    digest = f"{EMBEDDER_ID}:{corpus_fingerprint(corpus_dir)}"
    if index.current_fingerprint() == digest:
        logger.info("rag corpus unchanged")
        return
    chunks = load_chunks(corpus_dir)
    index.replace(chunks, digest)
    logger.info("rag corpus indexed chunks=%s", len(chunks))
