"""Graph state passed between planner, worker, and critic."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class PlanStep(TypedDict):
    kind: str
    server: str
    tool: str
    arguments: dict[str, str]
    reason: str


class ToolResult(TypedDict):
    server: str
    tool: str
    ok: bool
    output: dict[str, Any]
    error: str | None


class GraphState(TypedDict):
    query: str
    mode: str
    plan: list[PlanStep]
    tool_results: list[ToolResult]
    steps: Annotated[list[dict[str, str]], operator.add]
    accepted: bool
    critic_notes: str
    final: dict[str, Any]
