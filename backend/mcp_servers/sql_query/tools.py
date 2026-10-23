"""Read-only SQL against a tiny in-memory demo schema. No database connection."""

from __future__ import annotations

import json
from typing import Any

from mcp_servers.common.results import citation, fail, ok
from mcp_servers.sql_query.guard import demo_table, normalize_select

_ORDERS = (
    {"id": 1001, "status": "shipped", "total": "42.00"},
    {"id": 1002, "status": "processing", "total": "15.50"},
)
_DOCS = ({"id": "overview", "title": "Forge overview", "body": "Planner, worker, and critic."},)
_TABLES = {"orders": _ORDERS, "docs": _DOCS}


def sql_query(sql: str) -> dict[str, Any]:
    """Run a single read-only SELECT against the demo orders or docs table."""
    try:
        statement = normalize_select(sql)
        table = demo_table(statement)
    except ValueError as exc:
        return fail(str(exc))

    if table is None:
        return ok(sql=statement, rows=[], citations=[])

    rows = list(_TABLES[table])
    excerpt = json.dumps(rows[:2], separators=(",", ":"))
    cited = citation(f"sql:{table}", excerpt)
    citations = [cited] if cited is not None else []
    return ok(sql=statement, rows=rows, citations=citations)


TOOLS = {"sql_query": sql_query}
