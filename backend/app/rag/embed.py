"""Signed feature hashing into a fixed vector.

This is the local embedder so retrieval runs without a paid API key.
Shared tokens land in the same dimensions, and the vector is L2-normalized
for cosine search. It is not a neural embedding. A model can replace this
class without changing the index or the worker.
"""

from __future__ import annotations

import hashlib
import math

from app.rag.text import tokenize

EMBED_DIM = 384
EMBEDDER_ID = "signed-hash-384-min3-stop1"


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
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
