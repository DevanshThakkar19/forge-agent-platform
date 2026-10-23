"""Start a stub run and read it back."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_run_service, require_api_key
from app.evals.gate import GateBlocked
from app.schemas.runs import RunCreate, RunRecord
from app.services.runs import RunService

router = APIRouter(
    prefix="/v1/runs",
    tags=["runs"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=RunRecord, status_code=status.HTTP_201_CREATED)
def create_run(
    body: RunCreate,
    service: RunService = Depends(get_run_service),
) -> RunRecord:
    try:
        return service.create(query=body.query, mode=body.mode)
    except GateBlocked as exc:
        metrics = exc.decision.metrics
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "promote blocked",
                "reasons": list(exc.decision.reasons),
                "faithfulness": metrics.get("faithfulness"),
                "tool_success_rate": metrics.get("tool_success_rate"),
                "decision_accuracy": metrics.get("decision_accuracy"),
            },
        ) from exc


@router.get("/{run_id}", response_model=RunRecord)
def get_run(run_id: str, service: RunService = Depends(get_run_service)) -> RunRecord:
    record = service.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return record
