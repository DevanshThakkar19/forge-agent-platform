"""Build an MCP server from a tool map and serve it over stdio."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from mcp.server import MCPServer


def build_server(
    name: str,
    instructions: str,
    tools: Mapping[str, Callable[..., Any]],
) -> MCPServer:
    server = MCPServer(name, instructions=instructions)
    for fn in tools.values():
        server.tool()(fn)
    return server


def serve(server: MCPServer) -> None:
    server.run(transport="stdio")
