"""Prove each stub server speaks MCP over stdio, not only that it imports."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from app.mcp.registry import SERVER_TOOLS

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MODULES = {
    "web_search": "mcp_servers.web_search",
    "sql_query": "mcp_servers.sql_query",
    "file_store": "mcp_servers.file_store",
    "http_api": "mcp_servers.http_api",
}


async def _tool_names(module: str) -> list[str]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        cwd=_BACKEND_ROOT,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            return [tool.name for tool in listed.tools]


async def _call_web_search() -> dict:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.web_search"],
        cwd=_BACKEND_ROOT,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("web_search", {"query": "order 1001"})
            assert result.structured_content is not None
            return dict(result.structured_content)


def test_stdio_servers_list_their_catalog_tools() -> None:
    async def run() -> None:
        for key, module in _MODULES.items():
            assert await _tool_names(module) == list(SERVER_TOOLS[key])

        payload = await _call_web_search()
        assert payload["ok"] is True
        assert payload["stub"] is True

    asyncio.run(run())
