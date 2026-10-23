"""Score one golden task. No model judge.

Faithfulness is citation precision and recall against the locked sources,
then zeroed when the accept/reject decision or a required tool is wrong.
A correct reject scores 1. Tool success is counted separately.
"""

from __future__ import annotations

import math
from typing import Any

from app.evals.tasks import GoldenTask


def score_task(
    task: GoldenTask,
    *,
    accepted: bool | None,
    sources: list[str],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    called = [str(item.get("tool", "")) for item in tools]
    ok_flags = [item.get("ok") is True for item in tools]
    decision_ok = (accepted is True) == (task.expect == "accept")
    tools_ok = all(name in called for name in task.required_tools) and all(ok_flags)

    if task.expect == "reject":
        precision = None
        recall = None
        faithfulness = 1.0 if decision_ok else 0.0
    else:
        allowed = set(task.allowed_sources)
        precision = _precision(sources, allowed)
        recall = _recall(sources, task.required_sources)
        if decision_ok and tools_ok:
            faithfulness = _f1(precision, recall)
        else:
            faithfulness = 0.0

    return {
        "id": task.id,
        "expect": task.expect,
        "accepted": accepted,
        "decision_ok": decision_ok,
        "tools_ok": tools_ok,
        "faithfulness": round(faithfulness, 4),
        "precision": None if precision is None else round(precision, 4),
        "recall": None if recall is None else round(recall, 4),
        "sources": sources,
        "tools": called,
        "tool_calls": len(tools),
        "tool_failures": sum(1 for flag in ok_flags if not flag),
    }


def aggregate(rows: list[dict[str, Any]], latencies_ms: list[float]) -> dict[str, Any]:
    count = len(rows)
    faithfulness = sum(float(row["faithfulness"]) for row in rows) / count
    decisions = sum(1 for row in rows if row["decision_ok"]) / count
    calls = sum(int(row["tool_calls"]) for row in rows)
    failures = sum(int(row["tool_failures"]) for row in rows)
    tool_success = 1.0 if calls == 0 else (calls - failures) / calls
    return {
        "tasks": count,
        "faithfulness": round(faithfulness, 4),
        "decision_accuracy": round(decisions, 4),
        "tool_success_rate": round(tool_success, 4),
        "latency_p50_ms": round(percentile(latencies_ms, 50), 3),
        "latency_p95_ms": round(percentile(latencies_ms, 95), 3),
    }


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile. Index is ceil(pct/100 * n) - 1."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = math.ceil(pct / 100 * len(ordered)) - 1
    index = min(max(index, 0), len(ordered) - 1)
    return ordered[index]


def _precision(sources: list[str], allowed: set[str]) -> float:
    if not sources:
        return 0.0
    return sum(1 for source in sources if source in allowed) / len(sources)


def _recall(sources: list[str], required: list[str]) -> float:
    if not required:
        return 1.0
    found = set(sources)
    return sum(1 for source in required if source in found) / len(required)


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
