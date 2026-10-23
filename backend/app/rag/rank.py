"""Hybrid rank: cosine candidates, BM25 candidates, reciprocal rank fusion.

Postgres uses its own cosine operator and ts_rank for the two candidate lists.
Fusion stays here so both indexes share the merge rule.
"""

from __future__ import annotations

import math
from collections import Counter

from app.rag.text import tokenize
from app.rag.types import StoredChunk

VECTOR_MIN_COSINE = 0.2
_K1 = 1.2
_B = 0.75
_RRF_K = 60


def cosine(left: tuple[float, ...] | list[float], right: tuple[float, ...] | list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def vector_ranking(
    query_vector: list[float],
    chunks: list[StoredChunk],
    *,
    limit: int,
    min_cosine: float = VECTOR_MIN_COSINE,
) -> list[str]:
    scored: list[tuple[float, str]] = []
    for chunk in chunks:
        similarity = cosine(query_vector, chunk.embedding)
        if similarity >= min_cosine:
            scored.append((similarity, f"{chunk.source}#{chunk.chunk_index}"))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk_id for _, chunk_id in scored[:limit]]


def bm25_ranking(query: str, chunks: list[StoredChunk], *, limit: int) -> list[str]:
    tokens = tokenize(query)
    if not tokens or not chunks:
        return []
    documents = [tokenize(chunk.content) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(set(document))
    average_length = sum(len(document) for document in documents) / len(documents)
    if average_length == 0:
        return []

    scored: list[tuple[float, str]] = []
    for chunk, document in zip(chunks, documents, strict=True):
        frequencies = Counter(document)
        score = 0.0
        for term in set(tokens):
            freq = frequencies.get(term, 0)
            if freq == 0:
                continue
            seen_in = document_frequency[term]
            idf = math.log(1 + (len(documents) - seen_in + 0.5) / (seen_in + 0.5))
            denominator = freq + _K1 * (1 - _B + _B * len(document) / average_length)
            score += idf * (freq * (_K1 + 1)) / denominator
        if score > 0:
            scored.append((score, f"{chunk.source}#{chunk.chunk_index}"))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk_id for _, chunk_id in scored[:limit]]


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    *,
    k: int = _RRF_K,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
