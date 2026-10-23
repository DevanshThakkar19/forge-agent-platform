"""Unauthenticated liveness."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app import package_version
from app.graph.ollama import OllamaClient
from app.mcp.registry import SERVER_TOOLS
from app.schemas.health import HealthResponse

logger = logging.getLogger("forge.api")

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    database_ok = False
    try:
        database_ok = bool(request.app.state.database_probe.ping())
    except Exception:
        logger.warning("database probe failed", exc_info=True)
    settings = request.app.state.settings
    planner = "keyword"
    if (
        settings.planner == "local"
        and OllamaClient(
            settings.ollama_url,
            settings.ollama_model,
            settings.planner_timeout_s,
        ).reachable()
    ):
        planner = "local"
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        service="forge-api",
        version=package_version(),
        graph="stub",
        planner=planner,
        database="ok" if database_ok else "unavailable",
        mcp_servers=len(SERVER_TOOLS),
    )
