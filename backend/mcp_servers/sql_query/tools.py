"""Read-only SQL against the Postgres orders, docs, and cases tables."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp_servers.common.results import citation, fail, ok
from mcp_servers.sql_query.guard import demo_table, normalize_select
from mcp_servers.sql_query.store import fetch_rows

logger = logging.getLogger(__name__)


def sql_query(sql: str) -> dict[str, Any]:
    """Run one read-only SELECT. Search, files, and HTTP stay fixtures."""
    try:
        statement = normalize_select(sql)
        table = demo_table(statement)
    except ValueError as exc:
        return fail(str(exc))

    if table is None:
        return ok(sql=statement, rows=[], citations=[])

    try:
        rows = fetch_rows(statement)
    except Exception:
        logger.warning("sql query failed", exc_info=True)
        return fail("database unavailable")

    excerpt = json.dumps(rows[:2], separators=(",", ":"))
    cited = citation(f"sql:{table}", excerpt)
    citations = [cited] if cited is not None else []
    return ok(sql=statement, rows=rows, citations=citations)


TOOLS = {"sql_query": sql_query}
