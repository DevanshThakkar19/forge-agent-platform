"""Load markdown under a corpus directory into stable source ids."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.rag.chunk import chunk_text
from app.rag.types import RawChunk


def load_chunks(corpus_dir: Path) -> list[RawChunk]:
    root = corpus_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {root}")
    chunks: list[RawChunk] = []
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root).as_posix()
        source = f"corpus/{relative}"
        for index, text in enumerate(chunk_text(path.read_text(encoding="utf-8"))):
            chunks.append(RawChunk(source=source, chunk_index=index, content=text))
    return chunks


def corpus_fingerprint(corpus_dir: Path) -> str:
    hasher = hashlib.sha256()
    root = corpus_dir.resolve()
    paths = sorted(root.rglob("*.md")) if root.is_dir() else []
    for path in paths:
        hasher.update(path.relative_to(root).as_posix().encode())
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()
