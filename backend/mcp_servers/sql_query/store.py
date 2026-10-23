"""Read-only access to the Compose Postgres orders, docs, and cases tables.

The rows are the same Northline records as the corpus. The tool runs the
SELECT the planner sent. It does not return a hardcoded table.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

_DEFAULT_URL = "postgresql://forge:forge@localhost:5432/forge"

_ORDERS = (
    (1001, "shipped", "42.00"),
    (1002, "processing", "15.50"),
)
_DOCS = (("overview", "Forge overview", "Planner, worker, and critic."),)
_CASES = (
    (4401, "past due", "Brightmill. Amount due 120.00. Renewal is blocked."),
    (4402, "closed", "Harbor. Sign-in failed. Access was restored at 09:40."),
    (4408, "resolved", "Billing page was down for 14 minutes. Customers could not pay."),
    (4410, "waiting", "Lumen. Three seats were added to the workspace."),
)


def database_url() -> str:
    return os.environ.get("FORGE_DATABASE_URL", _DEFAULT_URL)


def fetch_rows(statement: str) -> list[dict[str, Any]]:
    with psycopg.connect(database_url(), connect_timeout=2, row_factory=dict_row) as conn:
        conn.autocommit = True
        _ensure(conn)
        conn.autocommit = False
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '2s'")
        fetched = conn.execute(statement).fetchall()
        conn.rollback()
    return [{key: _plain(value) for key, value in row.items()} for row in fetched]


def _ensure(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id int PRIMARY KEY,
            status text NOT NULL,
            total text NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS docs (
            id text PRIMARY KEY,
            title text NOT NULL,
            body text NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            id int PRIMARY KEY,
            status text NOT NULL,
            detail text NOT NULL
        )
        """
    )
    for row in _ORDERS:
        conn.execute(
            """
            INSERT INTO orders (id, status, total) VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, total = EXCLUDED.total
            """,
            row,
        )
    for row in _DOCS:
        conn.execute(
            """
            INSERT INTO docs (id, title, body) VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, body = EXCLUDED.body
            """,
            row,
        )
    for row in _CASES:
        conn.execute(
            """
            INSERT INTO cases (id, status, detail) VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, detail = EXCLUDED.detail
            """,
            row,
        )


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    return value
