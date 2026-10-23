"""HTTP API MCP server."""

from mcp_servers.common.bootstrap import build_server, serve
from mcp_servers.http_api.tools import TOOLS

SERVER_NAME = "forge-http-api"
INSTRUCTIONS = (
    "Call stub internal routes. Week 1 routes are /orders/1001 and /docs/overview. "
    "This server does not send network requests."
)

server = build_server(SERVER_NAME, INSTRUCTIONS, TOOLS)


def main() -> None:
    serve(server)
