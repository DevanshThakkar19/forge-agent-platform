"""In-memory run store. A Postgres store can replace this without changing routes."""

from __future__ import annotations

import threading

from app.schemas.runs import RunRecord


class InMemoryRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.Lock()

    def put(self, record: RunRecord) -> None:
        with self._lock:
            self._runs[record.id] = record

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)
