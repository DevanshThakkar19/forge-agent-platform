"""Run request and stored run record."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.answers import FinalAnswer


class RunMode(StrEnum):
    stub = "stub"
    promote = "promote"
    prod = "prod"


class RunStatus(StrEnum):
    completed = "completed"
    failed = "failed"


class RunCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "Save a note about order 1001 from the http api and sql table",
                    "mode": "stub",
                }
            ]
        }
    )

    query: str = Field(min_length=1, max_length=2000)
    mode: RunMode = RunMode.stub

    @field_validator("query")
    @classmethod
    def query_must_have_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be blank")
        return stripped


class RunStep(BaseModel):
    node: str
    detail: str


class RunRecord(BaseModel):
    id: str
    query: str
    mode: RunMode
    status: RunStatus
    accepted: bool | None = None
    critic_notes: str | None = None
    steps: list[RunStep] = Field(default_factory=list)
    result: FinalAnswer | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
    elapsed_ms: int | None = None
    tool_count: int | None = None
    tool_failures: int | None = None
    estimated_cost_usd: float | None = None
