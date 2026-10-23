"""HTTP routes backed by the Postgres orders, docs, and cases tables.

No outbound network call. Search and the file sandbox stay fixtures.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from mcp_servers.common.results import citation, fail, ok
from mcp_servers.sql_query.store import lookup_case, lookup_doc, lookup_order

logger = logging.getLogger(__name__)

_ORDER = re.compile(r"^/orders/(\d+)$")
_DOC = re.compile(r"^/docs/([a-z0-9_-]+)$")
_CASE = re.compile(r"^/cases/(\d+)$")


def http_get(path: str) -> dict[str, Any]:
    """GET one Postgres-backed route: /orders/{id}, /docs/{id}, or /cases/{id}."""
    if not isinstance(path, str) or not path.startswith("/") or ".." in path or "\\" in path:
        return fail("path must be a known route")
    try:
        body, excerpt = _load(path)
    except ValueError as exc:
        return fail(str(exc))
    except Exception:
        logger.warning("http route failed", exc_info=True)
        return fail("database unavailable")
    if body is None or excerpt is None:
        return fail("no record for that path")
    cited = citation(f"http_api:{path}", excerpt)
    citations = [cited] if cited is not None else []
    return ok(path=path, body=body, citations=citations)


def _load(path: str) -> tuple[dict[str, Any] | None, str | None]:
    order = _ORDER.fullmatch(path)
    if order:
        row = lookup_order(int(order.group(1)))
        if row is None:
            return None, None
        excerpt = f"Order {row['id']} is {row['status']} with total {row['total']}."
        return row, excerpt
    doc = _DOC.fullmatch(path)
    if doc:
        row = lookup_doc(doc.group(1))
        if row is None:
            return None, None
        return row, f"{row['title']}. {row['body']}"
    case = _CASE.fullmatch(path)
    if case:
        row = lookup_case(int(case.group(1)))
        if row is None:
            return None, None
        excerpt = f"Case {row['id']} is {row['status']}. {row['detail']}"
        return row, excerpt
    raise ValueError("no record for that path")


TOOLS = {"http_get": http_get}
