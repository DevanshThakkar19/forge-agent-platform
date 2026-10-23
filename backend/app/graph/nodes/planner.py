"""Planner. The keyword list is the default and the eval path.

A local model may choose the extra lookups. It never writes the answer.
The worker still receives a capped list of PlanStep values.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from app.graph.state import GraphState, PlanStep
from app.graph.understand import resolve_question, understand_prompt

NOTE_RELATIVE_PATH = "notes/run.txt"
_ORDERS_SQL = "SELECT id, status, total FROM orders"
_DOCS_SQL = "SELECT id, title, body FROM docs"
_CASES_SQL = "SELECT id, status, detail FROM cases"
_ORDERS_PATH = "/orders/1001"
_DOCS_PATH = "/docs/overview"


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(_has_word(text, word) for word in words)


def _step(
    kind: str,
    server: str,
    tool: str,
    arguments: dict[str, str],
    reason: str,
) -> PlanStep:
    return {
        "kind": kind,
        "server": server,
        "tool": tool,
        "arguments": arguments,
        "reason": reason,
    }


def build_plan(query: str, *, max_steps: int) -> list[PlanStep]:
    """Choose a retrieval step and stub tool calls from the query text."""
    if max_steps < 1:
        return []

    folded = query.lower()
    steps: list[PlanStep] = [
        _step(
            "retrieve",
            "rag",
            "retrieve",
            {"query": query},
            "hybrid retrieval over the corpus",
        ),
        _step(
            "tool",
            "web_search",
            "web_search",
            {"query": query},
            "search the fixture index",
        ),
    ]

    wants_orders = _has_any(folded, ("order", "orders"))
    wants_docs = _has_any(folded, ("doc", "docs", "documentation"))
    wants_cases = _has_any(folded, ("case", "cases"))
    use_docs = wants_docs and not wants_orders
    use_cases = wants_cases and not wants_orders and not wants_docs

    if use_cases or wants_orders or wants_docs or _has_any(folded, ("sql", "table", "select")):
        if use_cases:
            sql, reason = _CASES_SQL, "read the cases table"
        elif use_docs:
            sql, reason = _DOCS_SQL, "read the docs table"
        else:
            sql, reason = _ORDERS_SQL, "read the orders table"
        steps.append(
            _step(
                "tool",
                "sql_query",
                "sql_query",
                {"sql": sql},
                reason,
            )
        )

    if wants_orders or wants_docs or _has_any(folded, ("http", "api", "endpoint")):
        path = _DOCS_PATH if use_docs else _ORDERS_PATH
        steps.append(
            _step(
                "tool",
                "http_api",
                "http_get",
                {"path": path},
                f"read stub route {path}",
            )
        )

    if _has_any(folded, ("file", "save", "write", "note", "sandbox")):
        steps.append(
            _step(
                "tool",
                "file_store",
                "write_file",
                {
                    "path": NOTE_RELATIVE_PATH,
                    "content": f"stub note\nquery: {query.strip()}\n",
                },
                "store an artifact in the sandbox",
            )
        )

    return steps[:max_steps]


_MODEL_PROMPT = """Choose extra lookups for a support desk. Do not answer the question.
Reply with JSON only, shaped as {{"tools": []}}.
Allowed values:
- sql_orders and http_orders: an order, an order id, or the orders table
- sql_docs and http_docs: documentation, an overview, a writeup, or how the desk works
- sql_cases: a support case or a case id
- write_note: save, write, keep, record, or note
Use both names in a pair when that subject comes up.
Use [] for a company when none of those words apply.
Examples:
Question: look at the overview writeup
{{"tools": ["sql_docs", "http_docs"]}}
Question: keep a record of case 4401
{{"tools": ["sql_cases", "write_note"]}}
Question: Where is order 1001?
{{"tools": ["sql_orders", "http_orders"]}}
Question: What is case 4401?
{{"tools": ["sql_cases"]}}
Now choose only for this question.
Question: {query}
"""


def _detail(plan: list[PlanStep]) -> str:
    names = ", ".join(f"{step['server']}.{step['tool']}" for step in plan) or "none"
    return f"planned {len(plan)} call(s): {names}"


def _tools_from_reply(raw: str) -> list[str] | None:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        body = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict) or "tools" not in body:
        return None
    tools = body["tools"]
    if isinstance(tools, str):
        tools = [tools]
    if not isinstance(tools, list):
        return None
    names: list[str] = []
    for item in tools:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
    return names


def _optional_step(query: str, name: str) -> PlanStep | None:
    if name == "sql_orders":
        return _step(
            "tool",
            "sql_query",
            "sql_query",
            {"sql": _ORDERS_SQL},
            "read the orders table",
        )
    if name == "sql_docs":
        return _step(
            "tool",
            "sql_query",
            "sql_query",
            {"sql": _DOCS_SQL},
            "read the docs table",
        )
    if name == "sql_cases":
        return _step(
            "tool",
            "sql_query",
            "sql_query",
            {"sql": _CASES_SQL},
            "read the cases table",
        )
    if name == "http_orders":
        return _step(
            "tool",
            "http_api",
            "http_get",
            {"path": _ORDERS_PATH},
            f"read stub route {_ORDERS_PATH}",
        )
    if name == "http_docs":
        return _step(
            "tool",
            "http_api",
            "http_get",
            {"path": _DOCS_PATH},
            f"read stub route {_DOCS_PATH}",
        )
    if name == "write_note":
        return _step(
            "tool",
            "file_store",
            "write_file",
            {"path": NOTE_RELATIVE_PATH, "content": f"stub note\nquery: {query.strip()}\n"},
            "store an artifact in the sandbox",
        )
    return None


def _steps_from_model(query: str, tools: list[str], *, max_steps: int) -> list[PlanStep]:
    if max_steps < 1:
        return []
    steps: list[PlanStep] = [
        _step("retrieve", "rag", "retrieve", {"query": query}, "hybrid retrieval over the corpus"),
        _step("tool", "web_search", "web_search", {"query": query}, "search the fixture index"),
    ]
    chosen: set[str] = set()
    for name in tools:
        if name in chosen:
            continue
        if name in {"sql_orders", "sql_docs", "sql_cases"} and chosen & {
            "sql_orders",
            "sql_docs",
            "sql_cases",
        }:
            continue
        if name in {"http_orders", "http_docs"} and chosen & {"http_orders", "http_docs"}:
            continue
        step = _optional_step(query, name)
        if step is None:
            continue
        chosen.add(name)
        steps.append(step)
        if len(steps) >= max_steps:
            break
    return steps[:max_steps]


def plan_node(
    state: GraphState,
    *,
    max_steps: int,
    complete: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    query = state["query"]
    if complete is None:
        plan = build_plan(query, max_steps=max_steps)
        return {"plan": plan, "steps": [{"node": "planner", "detail": _detail(plan)}]}

    question = _read_question(query, complete)
    try:
        raw = complete(_MODEL_PROMPT.format(query=question.strip()))
        tools = _tools_from_reply(raw) if isinstance(raw, str) else None
    except Exception:
        tools = None
    if tools is None:
        plan = build_plan(question, max_steps=max_steps)
        detail = f"keyword list {_detail(plan)}"
        if question == query:
            detail = f"local model unavailable; {detail}"
    else:
        plan = _steps_from_model(question, tools, max_steps=max_steps)
        detail = f"local model {_detail(plan)}"
    if question != query:
        detail = f"local model read this as {question}; {detail}"
    update: dict[str, Any] = {"plan": plan, "steps": [{"node": "planner", "detail": detail}]}
    if question != query:
        update["query"] = question
    return update


def _read_question(query: str, complete: Callable[[str], str]) -> str:
    try:
        understood = resolve_question(query, complete(understand_prompt(query)))
    except Exception:
        return query
    if not understood:
        return query
    return understood
