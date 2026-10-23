"""Read-only checks for the demo SQL stub. This does not parse SQL for real."""

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
    """Return ``orders`` or ``docs`` when the statement names exactly one demo table."""
    folded = statement.lower()
    has_orders = re.search(r"\borders\b", folded) is not None
    has_docs = re.search(r"\bdocs\b", folded) is not None
    if has_orders and has_docs:
        raise ValueError("query must name one demo table: orders or docs")
    if has_orders:
        return "orders"
    if has_docs:
        return "docs"
    return None
