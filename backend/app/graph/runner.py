"""Invoke the compiled graph and return the critic's structured answer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.answers import FinalAnswer


@dataclass(frozen=True)
class GraphOutcome:
    accepted: bool
    critic_notes: str
    steps: list[dict[str, str]]
    final: FinalAnswer


def run_graph(graph: Any, *, query: str, mode: str) -> GraphOutcome:
    state = graph.invoke(
        {
            "query": query,
            "mode": mode,
            "plan": [],
            "tool_results": [],
            "steps": [],
            "accepted": False,
            "critic_notes": "",
            "final": {},
            "retries": 0,
        }
    )
    return GraphOutcome(
        accepted=bool(state["accepted"]),
        critic_notes=str(state["critic_notes"]),
        steps=list(state["steps"]),
        final=FinalAnswer.model_validate(state["final"]),
    )
