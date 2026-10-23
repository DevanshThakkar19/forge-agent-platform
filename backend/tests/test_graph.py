from pathlib import Path

from tests.conftest import memory_retriever
from tests.samples import HAPPY_QUERY

from app.config import Settings
from app.graph.builder import build_graph
from app.graph.nodes.critic import STUB_REJECT_CONFIDENCE
from app.graph.runner import run_graph
from app.mcp.client import InProcessToolClient


class _FailingClient:
    def call(self, server: str, tool: str, arguments: dict, *, timeout_s: float) -> dict:
        assert timeout_s > 0
        return {"ok": False, "stub": True, "error": "timeout", "citations": []}


def test_graph_happy_path(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        planner="keyword",
    )
    outcome = run_graph(
        build_graph(settings, InProcessToolClient(tmp_path), memory_retriever()),
        query=HAPPY_QUERY,
        mode="stub",
    )
    assert outcome.accepted is True
    assert [step["node"] for step in outcome.steps] == ["planner", "worker", "critic"]
    assert all(item.ok for item in outcome.final.tool_calls_summary)
    assert outcome.final.confidence == 0.5
    assert (tmp_path / "notes" / "run.txt").is_file()


def test_graph_rejects_tool_failure(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        planner="keyword",
        max_graph_steps=2,
    )
    outcome = run_graph(
        build_graph(settings, _FailingClient(), memory_retriever()),
        query=HAPPY_QUERY,
        mode="stub",
    )
    assert outcome.accepted is False
    assert outcome.final.confidence == STUB_REJECT_CONFIDENCE
    assert [item.ok for item in outcome.final.tool_calls_summary] == [True, False]
    assert outcome.critic_notes.startswith("rejected:")
    assert [step["node"] for step in outcome.steps].count("critic") == 2
    assert [step["detail"] for step in outcome.steps].count("one more pass") == 1
