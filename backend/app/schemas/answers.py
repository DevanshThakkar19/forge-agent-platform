"""Structured answer contract shared by the graph and the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(min_length=1, max_length=500)


class ToolCallSummary(BaseModel):
    server: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    ok: bool


class FinalAnswer(BaseModel):
    """Stub-path answer. ``confidence`` is a critic self-score, not a golden-set metric."""

    answer: str = Field(min_length=1)
    citations: list[Citation]
    tool_calls_summary: list[ToolCallSummary]
    confidence: float = Field(ge=0, le=1)
