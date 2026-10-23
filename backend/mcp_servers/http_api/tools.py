"""Stub HTTP API. No network calls."""

from __future__ import annotations

from typing import Any

from mcp_servers.common.results import citation, fail, ok

_ROUTES: dict[str, dict[str, Any]] = {
    "/orders/1001": {
        "body": {"id": 1001, "status": "shipped", "total": "42.00"},
        "excerpt": "Demo order 1001 is shipped with total 42.00.",
    },
    "/docs/overview": {
        "body": {"id": "overview", "title": "Forge overview"},
        "excerpt": "Forge routes a goal through a planner, a worker, and a critic.",
    },
}


def http_get(path: str) -> dict[str, Any]:
    """GET a stub internal route such as /orders/1001 or /docs/overview."""
    if not isinstance(path, str) or not path.startswith("/") or ".." in path or "\\" in path:
        return fail("path must be a stub route")
    route = _ROUTES.get(path)
    if route is None:
        return fail("no stub route for that path")
    cited = citation(f"http_api:{path}", str(route["excerpt"]))
    citations = [cited] if cited is not None else []
    return ok(path=path, body=route["body"], citations=citations)


TOOLS = {"http_get": http_get}
