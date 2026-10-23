"""Local-model planner. The completer is fake so the suite never calls Ollama."""

from pathlib import Path

from fastapi.testclient import TestClient
from tests.conftest import StaticProbe, memory_retriever

from app.config import Settings
from app.graph.builder import build_graph
from app.graph.nodes.planner import build_plan, plan_node
from app.graph.runner import run_graph
from app.graph.understand import resolve_question
from app.main import create_app
from app.mcp.client import InProcessToolClient


def test_model_opens_docs_without_the_keyword_triggers() -> None:
    def complete(_: str) -> str:
        return '{"tools": ["sql_docs", "http_docs"]}'

    result = plan_node(
        {"query": "look at the overview writeup"},
        max_steps=5,
        complete=complete,
    )
    assert result["steps"][0]["detail"].startswith("local model planned")
    assert [step["tool"] for step in result["plan"]] == [
        "retrieve",
        "web_search",
        "sql_query",
        "http_get",
    ]
    assert result["plan"][2]["arguments"]["sql"] == "SELECT id, title, body FROM docs"
    assert result["plan"][3]["arguments"]["path"] == "/docs/overview"
    keyword = build_plan("look at the overview writeup", max_steps=5)
    assert [step["tool"] for step in keyword] == ["retrieve", "web_search"]


def test_model_can_save_a_note_the_keyword_list_would_skip(tmp_path: Path) -> None:
    def complete(_: str) -> str:
        return '{"tools": ["write_note"]}'

    query = "What is case 4401?"
    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        planner="keyword",
    )
    outcome = run_graph(
        build_graph(
            settings,
            InProcessToolClient(tmp_path),
            memory_retriever(),
            planner_complete=complete,
        ),
        query=query,
        mode="stub",
    )
    assert outcome.accepted is True
    assert any(item.tool == "write_file" for item in outcome.final.tool_calls_summary)
    assert (tmp_path / "notes" / "run.txt").is_file()
    assert "write_file" not in [step["tool"] for step in build_plan(query, max_steps=5)]


def test_garbage_model_output_uses_the_keyword_list() -> None:
    def complete(_: str) -> str:
        return "I would look that up."

    result = plan_node({"query": "Where is order 1001?"}, max_steps=5, complete=complete)
    assert "keyword list" in result["steps"][0]["detail"]
    assert result["plan"][2]["arguments"]["sql"] == "SELECT id, status, total FROM orders"


def test_model_error_uses_the_keyword_list() -> None:
    def complete(_: str) -> str:
        raise TimeoutError("down")

    result = plan_node({"query": "Where is order 1001?"}, max_steps=5, complete=complete)
    assert result["steps"][0]["detail"].startswith("local model unavailable")
    assert result["plan"][3]["arguments"]["path"] == "/orders/1001"


def test_model_cannot_accept_an_unsupported_question(tmp_path: Path) -> None:
    def complete(_: str) -> str:
        return '{"tools": ["sql_orders", "http_orders", "write_note"]}'

    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        planner="keyword",
    )
    outcome = run_graph(
        build_graph(
            settings,
            InProcessToolClient(tmp_path),
            memory_retriever(),
            planner_complete=complete,
        ),
        query="order a pizza",
        mode="stub",
    )
    assert outcome.accepted is False
    assert outcome.critic_notes.startswith("rejected:")


def _reply(prompt: str, reading: str) -> str:
    if prompt.startswith("Read a messy"):
        return reading
    return '{"tools": []}'


def test_chatter_does_not_block_a_real_case(tmp_path: Path) -> None:
    reading = '{"question": "What is case 4401?", "chatter": ["bro", "dude", "common"]}'

    def complete(prompt: str) -> str:
        return _reply(prompt, reading)

    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        planner="keyword",
    )
    outcome = run_graph(
        build_graph(
            settings,
            InProcessToolClient(tmp_path),
            memory_retriever(),
            planner_complete=complete,
        ),
        query="What is case it about case 4401 bro dude common",
        mode="stub",
    )
    assert outcome.accepted is True
    assert "4401" in outcome.steps[0]["detail"]
    assert any(item.source == "corpus/cases/4401.md" for item in outcome.final.citations)


def test_a_forgotten_fact_is_still_checked(tmp_path: Path) -> None:
    def complete(prompt: str) -> str:
        return _reply(prompt, '{"question": "What is case 4401?", "chatter": ["bro"]}')

    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        planner="keyword",
    )
    outcome = run_graph(
        build_graph(
            settings,
            InProcessToolClient(tmp_path),
            memory_retriever(),
            planner_complete=complete,
        ),
        query="what is the password for case 4401 bro",
        mode="stub",
    )
    assert outcome.accepted is False
    assert "password" in outcome.critic_notes


def test_resolve_puts_a_dropped_number_back() -> None:
    text = resolve_question(
        "What is case 4401 bro",
        '{"question": "What is the case?", "chatter": ["bro"]}',
    )
    assert text is not None
    assert "4401" in text


def test_resolve_drops_a_word_the_person_did_not_say() -> None:
    text = resolve_question(
        "What is case 4401 bro",
        '{"question": "What is case 4401 refund?", "chatter": ["bro"]}',
    )
    assert text is not None
    assert "refund" not in text.lower()
    assert "4401" in text


def test_health_reports_keyword_when_the_local_model_is_down(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        planner="local",
        ollama_url="http://127.0.0.1:9",
    )
    application = create_app(
        settings,
        client=InProcessToolClient(tmp_path),
        retriever=memory_retriever(),
        database_probe=StaticProbe(False),
    )
    with TestClient(application) as client:
        body = client.get("/health").json()
    assert body["graph"] == "stub"
    assert body["planner"] == "keyword"
