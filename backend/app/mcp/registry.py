"""Tool catalog shared by the in-process client and the MCP servers.

Adding a server means a new package under ``mcp_servers`` plus one entry here.
The graph never imports a server module directly.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp_servers.file_store.tools import TOOLS as FILE_STORE_TOOLS
from mcp_servers.http_api.tools import TOOLS as HTTP_API_TOOLS
from mcp_servers.sql_query.tools import TOOLS as SQL_QUERY_TOOLS
from mcp_servers.web_search.tools import TOOLS as WEB_SEARCH_TOOLS

ToolFn = Callable[..., dict[str, Any]]

SERVER_TOOLS: dict[str, dict[str, ToolFn]] = {
    "web_search": WEB_SEARCH_TOOLS,
    "sql_query": SQL_QUERY_TOOLS,
    "file_store": FILE_STORE_TOOLS,
    "http_api": HTTP_API_TOOLS,
}

SERVER_MODULES: dict[str, str] = {
    "web_search": "mcp_servers.web_search",
    "sql_query": "mcp_servers.sql_query",
    "file_store": "mcp_servers.file_store",
    "http_api": "mcp_servers.http_api",
}


def tool_callable(server: str, tool: str) -> ToolFn | None:
    namespace = SERVER_TOOLS.get(server)
    if namespace is None:
        return None
    return namespace.get(tool)
