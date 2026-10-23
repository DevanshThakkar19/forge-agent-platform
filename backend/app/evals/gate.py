"""Promote gate. Fail closed when the measured baseline misses a threshold."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

FAITHFULNESS_MIN = 0.80
TOOL_SUCCESS_MIN = 0.90
DECISION_ACCURACY_MIN = 1.0


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    reasons: tuple[str, ...]
    metrics: dict


class GateBlocked(Exception):
    def __init__(self, decision: GateDecision) -> None:
        self.decision = decision
        super().__init__(decision.reasons[0] if decision.reasons else "promote blocked")


def decide(metrics: dict | None) -> GateDecision:
    if not metrics:
        return GateDecision(False, ("no measured baseline",), {})
    reasons: list[str] = []
    faithfulness = float(metrics.get("faithfulness") or 0)
    tool_success = float(metrics.get("tool_success_rate") or 0)
    decisions = float(metrics.get("decision_accuracy") or 0)
    if faithfulness < FAITHFULNESS_MIN:
        reasons.append(f"faithfulness {faithfulness:.4f} < {FAITHFULNESS_MIN:.2f}")
    if tool_success < TOOL_SUCCESS_MIN:
        reasons.append(f"tool success {tool_success:.4f} < {TOOL_SUCCESS_MIN:.2f}")
    if decisions < DECISION_ACCURACY_MIN:
        reasons.append(f"decision accuracy {decisions:.4f} < {DECISION_ACCURACY_MIN:.2f}")
    return GateDecision(not reasons, tuple(reasons), metrics)


def load_baseline(path: Path) -> dict | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("faithfulness") is None:
        return None
    return payload
