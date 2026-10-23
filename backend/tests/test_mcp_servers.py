import asyncio
import importlib

from app.mcp.registry import SERVER_TOOLS

_MODULES = {
    "web_search": "mcp_servers.web_search.server",
    "sql_query": "mcp_servers.sql_query.server",
    "file_store": "mcp_servers.file_store.server",
    "http_api": "mcp_servers.http_api.server",
}


def test_servers_compile_and_match_the_catalog() -> None:
    assert list(SERVER_TOOLS) == ["web_search", "sql_query", "file_store", "http_api"]
    for key, module_name in _MODULES.items():
        module = importlib.import_module(module_name)
        tools = asyncio.run(module.server.list_tools())
        assert [tool.name for tool in tools] == list(SERVER_TOOLS[key])
        assert module.server.name
        assert module.server.instructions
        assert callable(module.main)
