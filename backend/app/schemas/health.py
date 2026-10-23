"""Health payload. ``degraded`` means the process is up and Postgres is not."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: Literal["forge-api"]
    version: str
    graph: Literal["stub"]
    planner: Literal["keyword", "local"]
    database: Literal["ok", "unavailable"]
    mcp_servers: int
