"""Load the locked golden set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

BACKEND_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = BACKEND_ROOT / "evals" / "golden_set.jsonl"
BASELINE_DIR = BACKEND_ROOT / "evals" / "baselines"
CURRENT_BASELINE = BASELINE_DIR / "current.json"


class GoldenTask(BaseModel):
    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expect: str
    required_sources: list[str] = Field(default_factory=list)
    allowed_sources: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    sample: bool = False

    @model_validator(mode="after")
    def check_contract(self) -> GoldenTask:
        if self.expect not in {"accept", "reject"}:
            raise ValueError(f"{self.id} expect must be accept or reject")
        if self.expect == "reject":
            return self
        missing = [source for source in self.required_sources if source not in self.allowed_sources]
        if missing:
            raise ValueError(f"{self.id} required sources not allowed: {missing}")
        if not self.required_sources:
            raise ValueError(f"{self.id} accept task needs a required source")
        return self


def golden_sha256(path: Path = GOLDEN_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tasks(path: Path = GOLDEN_PATH) -> list[GoldenTask]:
    tasks: list[GoldenTask] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        task = GoldenTask.model_validate(json.loads(stripped))
        if task.id in seen:
            raise ValueError(f"duplicate task id {task.id} on line {line_number}")
        seen.add(task.id)
        tasks.append(task)
    if not 30 <= len(tasks) <= 50:
        raise ValueError(f"golden set must hold 30 to 50 tasks, found {len(tasks)}")
    if sum(1 for task in tasks if task.sample) < 5:
        raise ValueError("golden set needs at least 5 sample tasks for CI")
    return tasks
