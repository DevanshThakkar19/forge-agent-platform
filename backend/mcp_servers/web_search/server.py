"""Web search MCP server."""

from mcp_servers.common.bootstrap import build_server, serve
from mcp_servers.web_search.tools import TOOLS

SERVER_NAME = "forge-web-search"
INSTRUCTIONS = "Week 1 fixture search. Returns labeled stub snippets, not a live web index."

server = build_server(SERVER_NAME, INSTRUCTIONS, TOOLS)


def main() -> None:
    serve(server)
