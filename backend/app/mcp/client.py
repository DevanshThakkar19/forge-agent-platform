"""Tool client seam.

``InProcessToolClient`` calls the registered functions in this process.
``StdioToolClient`` is what the API uses. The worker only sees ``ToolClient``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from app.config import Settings
from app.mcp.registry import tool_callable
from mcp_servers.common.results import fail
from mcp_servers.file_store.sandbox import use_sandbox

logger = logging.getLogger("forge.mcp")


class ToolClient(Protocol):
    def call(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any],
        *,
        timeout_s: float,
    ) -> dict[str, Any]:
        """Run one tool and return a payload with an ``ok`` boolean."""


class InProcessToolClient:
    def __init__(self, sandbox_root: Path) -> None:
        self._sandbox_root = Path(sandbox_root).resolve()

    def call(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any],
        *,
        timeout_s: float,
    ) -> dict[str, Any]:
        if timeout_s <= 0:
            return fail("invalid timeout")
        fn = tool_callable(server, tool)
        if fn is None:
            return fail(f"unknown tool {server}.{tool}")
        try:
            if server == "file_store":
                with use_sandbox(self._sandbox_root):
                    output = fn(**dict(arguments))
            else:
                output = fn(**dict(arguments))
        except Exception:
            logger.warning("tool %s.%s raised", server, tool, exc_info=True)
            return fail("tool raised an unexpected error")
        if not isinstance(output, dict) or not isinstance(output.get("ok"), bool):
            return fail("tool returned an invalid payload")
        return output


def build_tool_client(settings: Settings) -> ToolClient:
    if settings.tool_transport == "inprocess":
        return InProcessToolClient(settings.sandbox_root)
    from app.mcp.stdio import StdioToolClient

    client = StdioToolClient(settings.sandbox_root)
    client.start()
    return client
