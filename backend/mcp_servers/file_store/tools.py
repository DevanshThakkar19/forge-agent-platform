"""Read and write text files inside a sandbox directory."""

from __future__ import annotations

from typing import Any

from mcp_servers.common.results import citation, fail, ok
from mcp_servers.file_store.sandbox import resolve_sandbox_path

MAX_FILE_CHARS = 65_536


def read_file(path: str) -> dict[str, Any]:
    """Read a UTF-8 text file from the sandbox. Paths are relative to the sandbox root."""
    try:
        target = resolve_sandbox_path(path)
    except ValueError as exc:
        return fail(str(exc))
    if not target.is_file():
        return fail("file not found")
    content = target.read_text(encoding="utf-8")
    cited = citation(f"file:{path}", content)
    citations = [cited] if cited is not None else []
    return ok(path=path, content=content, citations=citations)


def write_file(path: str, content: str) -> dict[str, Any]:
    """Write a UTF-8 text file inside the sandbox. Parent directories are created."""
    if not isinstance(content, str):
        return fail("content must be text")
    if len(content) > MAX_FILE_CHARS:
        return fail(f"content exceeds {MAX_FILE_CHARS} characters")
    try:
        target = resolve_sandbox_path(path)
    except ValueError as exc:
        return fail(str(exc))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    cited = citation(f"file:{path}", content)
    citations = [cited] if cited is not None else []
    return ok(path=path, citations=citations)


TOOLS = {"read_file": read_file, "write_file": write_file}
