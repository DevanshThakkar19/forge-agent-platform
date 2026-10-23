"""Read-only checks before a SELECT is sent to Postgres."""

from __future__ import annotations

import re

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|copy|attach)\b",
    re.IGNORECASE,
)


def normalize_select(sql: str) -> str:
    """Return a single SELECT, or raise ValueError with a client-safe message."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("empty sql")
    statement = sql.strip()
    if statement.endswith(";"):
        statement = statement[:-1].strip()
    if ";" in statement or "--" in statement or "/*" in statement:
        raise ValueError("single read-only statement only")
    if not re.match(r"select\b", statement, flags=re.IGNORECASE):
        raise ValueError("read-only select only")
    if _FORBIDDEN.search(statement):
        raise ValueError("read-only select only")
    return statement


def demo_table(statement: str) -> str | None:
    """Return the one allowed table named in the statement."""
    folded = statement.lower()
    if re.search(r"\b(pg_\w+|information_schema)\b", folded):
        raise ValueError("read-only select only")
    names = [name for name in ("orders", "docs", "cases") if re.search(rf"\b{name}\b", folded)]
    if len(names) > 1:
        raise ValueError("query must name one table: orders, docs, or cases")
    if not names:
        return None
    return names[0]
