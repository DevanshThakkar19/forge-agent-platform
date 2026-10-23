"""Accept a stub answer only when every call succeeded and something was cited.

Confidence values here are critic self-scores for this path. They are not
faithfulness, and they must not be copied into a resume or baseline file.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from app.graph.state import GraphState
from app.rag.text import support_tokens, tokenize
from app.schemas.answers import Citation, FinalAnswer, ToolCallSummary

_QUESTION = frozenset({"where", "which", "please", "could", "would", "check", "tell"})
_NUMBER = re.compile(r"\d+")
_ORDER_ID = re.compile(r"\border\s+(\d+)\b", re.IGNORECASE)
_RECORD_ID = re.compile(r'"id"\s*:\s*"?(\d+)"?')
STUB_ACCEPT_CONFIDENCE = 0.5
STUB_REJECT_CONFIDENCE = 0.2
_MAX_CITATIONS = 8


def critique_node(state: GraphState) -> dict[str, Any]:
    results = list(state["tool_results"])
    citations: list[Citation] = []
    summaries: list[ToolCallSummary] = []
    failed: list[str] = []

    for result in results:
        name = f"{result['server']}.{result['tool']}"
        summaries.append(
            ToolCallSummary(server=result["server"], tool=result["tool"], ok=result["ok"])
        )
        if not result["ok"]:
            failed.append(name)
            continue
        for raw in result["output"].get("citations") or []:
            try:
                citations.append(Citation.model_validate(raw))
            except ValidationError:
                continue

    citations = citations[:_MAX_CITATIONS]
    accepted, notes, answer, confidence = _judge(state["query"], results, failed, citations)
    final = FinalAnswer(
        answer=answer,
        citations=citations,
        tool_calls_summary=summaries,
        confidence=confidence,
    )
    return {
        "accepted": accepted,
        "critic_notes": notes,
        "final": final.model_dump(),
        "steps": [{"node": "critic", "detail": notes}],
    }


def _judge(
    query: str,
    results: list[dict[str, Any]],
    failed: list[str],
    citations: list[Citation],
) -> tuple[bool, str, str, float]:
    if failed:
        names = ", ".join(failed)
        return (
            False,
            f"rejected: {names}",
            f"Cannot support a conclusion. Failed stub calls: {names}.",
            STUB_REJECT_CONFIDENCE,
        )
    if not citations:
        return (
            False,
            "rejected: empty retrieval",
            "Cannot support a conclusion because the stub tools returned no citations.",
            STUB_REJECT_CONFIDENCE,
        )
    missing = _unsupported(query, citations)
    if missing:
        names = ", ".join(missing)
        return (
            False,
            f"rejected: unsupported {names}",
            f"Cannot support a conclusion. Query terms missing from evidence: {names}.",
            STUB_REJECT_CONFIDENCE,
        )

    bits: list[str] = []
    for result in results:
        raw_cites = result["output"].get("citations") or []
        if raw_cites and isinstance(raw_cites[0], dict):
            source = str(raw_cites[0].get("source", "")).strip()
            if source:
                bits.append(f"{result['tool']} cited {source}")
    joined = "; ".join(bits)
    answer = f"Stub answer for {query.strip()!r}. Citations: {joined}."
    return True, "accepted cited evidence", answer, STUB_ACCEPT_CONFIDENCE


def checked_terms(query: str) -> list[str]:
    """Words the critic has to find in the records. Short words and question words are skipped."""
    terms: list[str] = []
    for token in tokenize(query):
        if len(token) < 5 or token in _QUESTION or not support_tokens(token):
            continue
        if token not in terms:
            terms.append(token)
    return terms


def _unsupported(query: str, citations: list[Citation]) -> list[str]:
    evidence = " ".join(item.excerpt for item in citations if not item.source.startswith("file:"))
    have = support_tokens(evidence)
    have_numbers = set(_NUMBER.findall(evidence))
    known_orders = set(_ORDER_ID.findall(evidence)) | set(_RECORD_ID.findall(evidence))
    missing: list[str] = []
    for token in checked_terms(query):
        if token in have or token in missing:
            continue
        missing.append(token)
    for number in _ORDER_ID.findall(query):
        if number not in known_orders and number not in missing:
            missing.append(number)
    for number in _NUMBER.findall(query):
        if number in have_numbers or number in missing:
            continue
        missing.append(number)
    return missing
