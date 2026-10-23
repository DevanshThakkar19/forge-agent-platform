"""Local embedders. Both return a 384-d L2-normalized vector.

The live path is a small neural model (all-MiniLM-L6-v2 via ONNX).
The hashing class stays so a unit test can still check that older method.
Neither calls a paid API.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.rag.text import tokenize

EMBED_DIM = 384
EMBEDDER_ID = "fastembed-minilm-l6-v2-384"
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class MiniLMEmbedder:
    """Local neural embedder. The weights load once, on the first call."""

    def __init__(self, dim: int = EMBED_DIM) -> None:
        if dim != EMBED_DIM:
            raise ValueError("MiniLM writes 384 dimensions")
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        rows: list[list[float]] = []
        for vector in _minilm().embed(texts):
            values = [float(item) for item in vector]
            rows.append(_normalize(values))
        return rows


def _minilm():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model


class HashingEmbedder:
    def __init__(self, dim: int = EMBED_DIM) -> None:
        if dim < 8:
            raise ValueError("embedding dimension must be at least 8")
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    def _one(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return _normalize(vector)


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
