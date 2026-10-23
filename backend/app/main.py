"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app import package_version
from app.api.router import api_router
from app.config import Settings, get_settings
from app.logging import setup_logging
from app.mcp.client import ToolClient, build_tool_client
from app.mcp.registry import SERVER_TOOLS
from app.rag.factory import build_retriever
from app.rag.postgres import DatabaseProbe, PgDatabaseProbe
from app.rag.retrieve import Retriever
from app.services.runs import RunService

logger = logging.getLogger("forge.api")


def create_app(
    settings: Settings | None = None,
    *,
    client: ToolClient | None = None,
    retriever: Retriever | None = None,
    database_probe: DatabaseProbe | None = None,
) -> FastAPI:
    resolved = settings or get_settings()
    setup_logging(resolved.log_level)
    tool_client = client if client is not None else build_tool_client(resolved)
    rag = (
        retriever
        if retriever is not None
        else build_retriever(
            resolved.database_url,
            resolved.corpus_dir,
            limit=resolved.retrieve_limit,
        )
    )
    probe = database_probe if database_probe is not None else PgDatabaseProbe(resolved.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        closer = getattr(app.state.tool_client, "close", None)
        if closer is not None:
            closer()

    app = FastAPI(
        title="Forge",
        version=package_version(),
        summary="Agentic workflow platform",
        description=(
            "Planner, worker, and critic over four MCP tool servers and a hybrid index. "
            "Metrics come from the committed golden-set baseline. "
            "An optional local model may choose lookups. "
            "The critic still refuses an answer the records do not support. "
            "There is no paid model on the request path."
        ),
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.tool_client = tool_client
    app.state.database_probe = probe
    app.state.run_service = RunService(resolved, client=tool_client, retriever=rag)
    app.include_router(api_router)
    logger.info("forge api ready mcp_servers=%s", len(SERVER_TOOLS))
    return app


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:create_app",
        host=settings.host,
        port=settings.port,
        factory=True,
    )
