"""SQL query MCP server."""

from mcp_servers.common.bootstrap import build_server, serve
from mcp_servers.sql_query.tools import TOOLS

SERVER_NAME = "forge-sql-query"
INSTRUCTIONS = (
    "Read-only SELECT against the demo orders and docs tables. "
    "This Week 1 server returns fixtures and does not open Postgres."
)

server = build_server(SERVER_NAME, INSTRUCTIONS, TOOLS)


def main() -> None:
    serve(server)
