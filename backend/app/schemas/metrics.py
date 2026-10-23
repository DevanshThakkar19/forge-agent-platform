"""Metrics from the latest golden-set baseline. Null until that file exists."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MetricsResponse(BaseModel):
    status: Literal["not_measured", "measured"] = "not_measured"
    faithfulness: float | None = None
    decision_accuracy: float | None = None
    tool_success_rate: float | None = None
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    estimated_cost_usd_per_success: float | None = None
    tasks: int | None = None
    baseline_id: str | None = None
    runtime: str | None = None
    golden_sha256: str | None = None
    note: str = Field(
        default=(
            "Golden-set metrics are not measured yet. "
            "Do not cite faithfulness, latency, or cost numbers from this endpoint."
        )
    )
