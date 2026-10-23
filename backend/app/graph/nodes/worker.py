"""Execute retrieval and the planner's tool calls."""

from __future__ import annotations

import logging
from typing import Any

from app.graph.state import GraphState, ToolResult
from app.mcp.client import ToolClient
from app.rag.retrieve import Retriever

logger = logging.getLogger("forge.graph")


def work_node(
    state: GraphState,
    *,
    client: ToolClient,
    retriever: Retriever,
    max_steps: int,
    timeout_s: float,
) -> dict[str, Any]:
    plan = list(state["plan"])[:max_steps]
    results: list[ToolResult] = []
    bits: list[str] = []

    for step in plan:
        output = _execute(step, state["query"], client, retriever, timeout_s)
        if not isinstance(output, dict):
            output = {"ok": False, "error": "invalid payload", "citations": []}
        ok = output.get("ok") is True
        raw_error = output.get("error")
        error = str(raw_error) if raw_error else None
        results.append(
            {
                "server": step["server"],
                "tool": step["tool"],
                "ok": ok,
                "output": output,
                "error": error,
            }
        )
        status = "ok" if ok else "failed"
        bits.append(f"{step['server']}.{step['tool']} {status}")

    detail = "; ".join(bits) if bits else "no calls"
    return {
        "tool_results": results,
        "steps": [{"node": "worker", "detail": detail}],
    }


def _execute(
    step: dict[str, Any],
    query: str,
    client: ToolClient,
    retriever: Retriever,
    timeout_s: float,
) -> dict[str, Any]:
    if step.get("kind") == "retrieve":
        text = str(step.get("arguments", {}).get("query") or query)
        try:
            return retriever.retrieve(text)
        except Exception:
            logger.warning("retriever raised", exc_info=True)
            return {"ok": False, "error": "retrieval failed", "citations": []}
    arguments = step.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}
    return client.call(
        str(step["server"]),
        str(step["tool"]),
        arguments,
        timeout_s=timeout_s,
    )
