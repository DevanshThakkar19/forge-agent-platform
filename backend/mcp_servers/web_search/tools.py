"""Fixture search index. Not a live web client."""

from __future__ import annotations

import re
from typing import Any

from mcp_servers.common.results import citation, fail, ok

_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "source": "fixture://forge/overview",
        "excerpt": "Forge routes a goal through a planner, a worker, and a critic over MCP tools.",
        "tokens": ("forge", "planner", "critic", "mcp"),
    },
    {
        "source": "fixture://forge/orders",
        "excerpt": "Demo order 1001 is shipped. The sql_query and http_api stubs both expose it.",
        "tokens": ("order", "orders", "1001"),
    },
)


def _has_token(text: str, token: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", text) is not None


def web_search(query: str) -> dict[str, Any]:
    """Search the Week 1 fixture index. Returns stub snippets, not a live web index."""
    if not isinstance(query, str):
        return fail("query must be text")
    cleaned = " ".join(query.split())
    if not cleaned:
        return ok(query=query, snippets=[], citations=[])

    haystack = cleaned.lower()
    hits = [
        item for item in _FIXTURES if any(_has_token(haystack, token) for token in item["tokens"])
    ]
    snippets = []
    for item in hits:
        cited = citation(str(item["source"]), str(item["excerpt"]))
        if cited is not None:
            snippets.append(cited)
    return ok(query=cleaned, snippets=snippets, citations=list(snippets))


TOOLS = {"web_search": web_search}
