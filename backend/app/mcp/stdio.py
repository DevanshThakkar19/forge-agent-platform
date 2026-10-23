"""Stdio MCP client. One long-lived session per server, calls from the worker thread.

Sessions stay on a private event loop. ``timeout_s`` bounds ``call_tool``.
The sandbox path is passed to the file_store process as FORGE_SANDBOX_ROOT.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from app.mcp.registry import SERVER_MODULES
from mcp_servers.common.results import fail

logger = logging.getLogger("forge.mcp")


def _server_cwd() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "mcp_servers").is_dir():
        return candidate
    return None


class StdioToolClient:
    def __init__(self, sandbox_root: Path, *, python: str | None = None) -> None:
        self._sandbox_root = Path(sandbox_root).resolve()
        self._python = python or sys.executable
        self._cwd = _server_cwd()
        self._loop = asyncio.new_event_loop()
        self._loop_ready = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, name="forge-mcp", daemon=True)
        self._stack: AsyncExitStack | None = None
        self._sessions: dict[str, ClientSession] = {}
        self._start_error: str | None = None
        self._closed = False
        self._thread.start()

    def start(self) -> None:
        if not self._loop_ready.wait(timeout=5):
            self._start_error = "mcp session unavailable"
            logger.error("mcp event loop did not start")
            return
        future = asyncio.run_coroutine_threadsafe(self._open_all(), self._loop)
        try:
            future.result(timeout=30)
        except Exception:
            logger.exception("failed to start mcp servers")
            self._start_error = "mcp session unavailable"

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
        if self._start_error is not None:
            return fail(self._start_error)
        if not self._loop_ready.is_set():
            return fail("mcp session unavailable")
        future = asyncio.run_coroutine_threadsafe(
            self._call(server, tool, arguments, timeout_s),
            self._loop,
        )
        try:
            return future.result(timeout=timeout_s + 2)
        except TimeoutError:
            future.cancel()
            return fail("tool timed out")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._loop_ready.is_set():
            future = asyncio.run_coroutine_threadsafe(self._aclose(), self._loop)
            try:
                future.result(timeout=10)
            except Exception:
                logger.exception("failed to close mcp sessions")
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.call_soon(self._loop_ready.set)
        self._loop.run_forever()

    async def _open_all(self) -> None:
        stack = AsyncExitStack()
        await stack.__aenter__()
        self._stack = stack
        env = dict(os.environ)
        env["FORGE_SANDBOX_ROOT"] = str(self._sandbox_root)
        for key, module in SERVER_MODULES.items():
            params = StdioServerParameters(
                command=self._python,
                args=["-m", module],
                cwd=self._cwd,
                env=env,
            )
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._sessions[key] = session
        logger.info("stdio mcp servers ready count=%s", len(self._sessions))

    async def _call(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any],
        timeout_s: float,
    ) -> dict[str, Any]:
        session = self._sessions.get(server)
        if session is None:
            return fail(f"unknown tool {server}.{tool}")
        try:
            result = await asyncio.wait_for(
                session.call_tool(tool, dict(arguments)),
                timeout=timeout_s,
            )
        except TimeoutError:
            return fail("tool timed out")
        except Exception:
            logger.warning("tool %s.%s raised over stdio", server, tool, exc_info=True)
            return fail("tool raised an unexpected error")
        payload = result.structured_content
        if isinstance(payload, dict) and isinstance(payload.get("ok"), bool):
            return dict(payload)
        return fail("tool returned an invalid payload")

    async def _aclose(self) -> None:
        stack = self._stack
        self._stack = None
        self._sessions.clear()
        if stack is not None:
            await stack.aclose()
