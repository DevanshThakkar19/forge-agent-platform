"""Latest golden-set baseline. Unmeasured when the file is missing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import require_api_key
from app.evals.gate import load_baseline
from app.schemas.metrics import MetricsResponse

router = APIRouter(
    prefix="/v1/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=MetricsResponse)
def get_metrics(request: Request) -> MetricsResponse:
    payload = load_baseline(request.app.state.settings.baseline_path)
    if payload is None:
        return MetricsResponse()
    return MetricsResponse(
        status="measured",
        faithfulness=payload.get("faithfulness"),
        decision_accuracy=payload.get("decision_accuracy"),
        tool_success_rate=payload.get("tool_success_rate"),
        latency_p50_ms=payload.get("latency_p50_ms"),
        latency_p95_ms=payload.get("latency_p95_ms"),
        estimated_cost_usd_per_success=payload.get("estimated_cost_usd_per_success"),
        tasks=payload.get("tasks"),
        baseline_id=payload.get("id"),
        runtime=payload.get("runtime"),
        golden_sha256=payload.get("golden_sha256"),
        note=str(payload.get("cost_basis") or ""),
    )
