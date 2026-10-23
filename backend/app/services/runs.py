"""Create a run, execute the stub graph, and store the record.

Execution is synchronous in this slice. POST /v1/runs returns after the critic
finishes. A critic rejection is status=completed with accepted=false. status=failed
means the graph raised.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.config import Settings
from app.evals.gate import GateBlocked, decide, load_baseline
from app.graph.builder import build_graph
from app.graph.runner import run_graph
from app.mcp.client import ToolClient
from app.obs.cost import ESTIMATED_USD_PER_TASK
from app.rag.retrieve import Retriever
from app.schemas.runs import RunMode, RunRecord, RunStatus, RunStep
from app.services.store import InMemoryRunStore

logger = logging.getLogger("forge.runs")

_GATED = {RunMode.promote, RunMode.prod}


class RunService:
    def __init__(
        self,
        settings: Settings,
        *,
        client: ToolClient | None = None,
        retriever: Retriever | None = None,
        store: InMemoryRunStore | None = None,
    ) -> None:
        self._store = store or InMemoryRunStore()
        self._settings = settings
        self._graph = build_graph(settings, client, retriever)

    def create(self, *, query: str, mode: RunMode) -> RunRecord:
        if mode in _GATED:
            decision = decide(load_baseline(self._settings.baseline_path))
            if not decision.passed:
                raise GateBlocked(decision)
        run_id = str(uuid4())
        started = datetime.now(UTC)
        try:
            outcome = run_graph(self._graph, query=query, mode=mode.value)
        except Exception as exc:
            logger.exception("run %s failed", run_id)
            finished = datetime.now(UTC)
            record = RunRecord(
                id=run_id,
                query=query,
                mode=mode,
                status=RunStatus.failed,
                error=f"{type(exc).__name__}: {exc}",
                created_at=started,
                finished_at=finished,
                elapsed_ms=_elapsed_ms(started, finished),
            )
        else:
            finished = datetime.now(UTC)
            record = RunRecord(
                id=run_id,
                query=query,
                mode=mode,
                status=RunStatus.completed,
                accepted=outcome.accepted,
                critic_notes=outcome.critic_notes,
                steps=[RunStep.model_validate(step) for step in outcome.steps],
                result=outcome.final,
                created_at=started,
                finished_at=finished,
                elapsed_ms=_elapsed_ms(started, finished),
                tool_count=len(outcome.final.tool_calls_summary),
                tool_failures=sum(1 for item in outcome.final.tool_calls_summary if not item.ok),
                estimated_cost_usd=ESTIMATED_USD_PER_TASK,
            )
            logger.info(
                "run %s finished status=%s accepted=%s",
                run_id,
                record.status.value,
                record.accepted,
            )
        self._store.put(record)
        return record

    def get(self, run_id: str) -> RunRecord | None:
        return self._store.get(run_id)


def _elapsed_ms(started: datetime, finished: datetime) -> int:
    return max(0, int((finished - started).total_seconds() * 1000))
