"""Records passed between the corpus loader, the index, and the retriever."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawChunk:
    source: str
    chunk_index: int
    content: str


@dataclass(frozen=True)
class StoredChunk:
    source: str
    chunk_index: int
    content: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class Hit:
    source: str
    chunk_index: int
    content: str
    score: float


def chunk_id(source: str, chunk_index: int) -> str:
    return f"{source}#{chunk_index}"
