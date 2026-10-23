"""Sandbox path checks for the file_store tool.

The override context var lets the API pass Settings.sandbox_root without putting
that path in the MCP tool schema.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

_override: ContextVar[Path | None] = ContextVar("forge_sandbox_root", default=None)
_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


def sandbox_root() -> Path:
    override = _override.get()
    if override is not None:
        return override
    return Path(os.environ.get("FORGE_SANDBOX_ROOT", "var/sandbox"))


@contextmanager
def use_sandbox(root: Path) -> Iterator[None]:
    token = _override.set(Path(root))
    try:
        yield
    finally:
        _override.reset(token)


def resolve_sandbox_path(relative: str) -> Path:
    """Resolve a relative sandbox path or raise ValueError before any file IO."""
    if not isinstance(relative, str) or not _PATH.fullmatch(relative):
        raise ValueError("path must stay inside the sandbox")
    if "\\" in relative or any(part in {".", ".."} for part in Path(relative).parts):
        raise ValueError("path must stay inside the sandbox")

    root = sandbox_root().resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path must stay inside the sandbox")
    return candidate
