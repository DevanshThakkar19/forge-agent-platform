from tests.conftest import CORPUS_DIR

from app.rag.chunk import chunk_text
from app.rag.corpus import load_chunks
from app.rag.embed import HashingEmbedder
from app.rag.memory import MemoryHybridIndex


def test_chunk_text_keeps_short_text_and_overlaps_long_text() -> None:
    assert chunk_text("short note") == ["short note"]
    chunks = chunk_text("x" * 200, size=80, overlap=20)
    assert len(chunks) >= 2
    assert chunks[0][-20:] == chunks[1][:20]


def test_embedder_is_normalized_and_stable() -> None:
    embedder = HashingEmbedder()
    first, second = embedder.embed(["order 1001", "order 1001"])
    assert first == second
    norm = sum(value * value for value in first) ** 0.5
    assert abs(norm - 1) < 1e-6


def test_memory_index_cites_orders_and_ignores_unrelated_text() -> None:
    index = MemoryHybridIndex()
    index.replace(load_chunks(CORPUS_DIR))
    hits = index.search("shipped order 1001", limit=3)
    assert hits
    assert hits[0].source == "corpus/orders.md"
    assert index.search("banana milkshake", limit=3) == []
