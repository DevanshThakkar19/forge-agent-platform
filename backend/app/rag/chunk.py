"""Character windows with overlap. Short documents stay one chunk."""

from __future__ import annotations


def chunk_text(text: str, *, size: int = 500, overlap: int = 80) -> list[str]:
    if size < 1:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be smaller than the chunk size")
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks
