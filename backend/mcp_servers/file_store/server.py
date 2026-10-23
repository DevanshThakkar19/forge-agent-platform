"""File store MCP server."""

from mcp_servers.common.bootstrap import build_server, serve
from mcp_servers.file_store.tools import TOOLS

SERVER_NAME = "forge-file-store"
INSTRUCTIONS = (
    "Read and write UTF-8 text files inside the Forge sandbox. "
    "Paths are relative. The server refuses paths that leave the sandbox."
)

server = build_server(SERVER_NAME, INSTRUCTIONS, TOOLS)


def main() -> None:
    serve(server)
