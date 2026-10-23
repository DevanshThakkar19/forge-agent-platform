"""Cost label for this stack.

Nothing in the request path calls a paid model or a paid search API.
The figure is an estimate of external spend, and that spend is zero.
"""

from __future__ import annotations

ESTIMATED_USD_PER_TASK = 0.0
COST_BASIS = (
    "no paid model or search API; local MiniLM embedder; "
    "sql reads Postgres; search, files, and http stay fixtures; estimate 0 USD per task"
)
