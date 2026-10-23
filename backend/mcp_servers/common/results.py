"""Shared helpers for MCP tool payloads."""

from __future__ import annotations

from typing import Any


def citation(source: str, excerpt: str) -> dict[str, str] | None:
    cleaned_source = source.strip()[:200]
    cleaned_excerpt = excerpt.strip()[:240]
    if not cleaned_source or not cleaned_excerpt:
        return None
    return {"source": cleaned_source, "excerpt": cleaned_excerpt}


def ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, "stub": True, **payload}


def fail(error: str, **payload: Any) -> dict[str, Any]:
    return {"ok": False, "stub": True, "error": error, "citations": [], **payload}
