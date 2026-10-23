"""Golden set, published baseline, and the promote gate."""

import json

from fastapi.testclient import TestClient
from tests.conftest import StaticProbe, memory_retriever

from app.config import Settings
from app.evals.gate import decide
from app.evals.runner import build_report
from app.evals.tasks import CURRENT_BASELINE, load_tasks
from app.main import create_app
from app.mcp.client import InProcessToolClient


def test_fresh_run_matches_the_published_baseline() -> None:
    report = build_report("check", load_tasks())
    saved = json.loads(CURRENT_BASELINE.read_text(encoding="utf-8"))
    for key in (
        "faithfulness",
        "decision_accuracy",
        "tool_success_rate",
        "tasks",
        "golden_sha256",
        "estimated_cost_usd_per_success",
    ):
        assert report[key] == saved[key]
    assert saved["gate_passed"] is True
    assert report["failures"] == []
    assert saved["runtime"] == "inprocess+memory"


def test_v0_baseline_fails_the_gate() -> None:
    v0 = json.loads((CURRENT_BASELINE.parent / "v0.json").read_text(encoding="utf-8"))
    decision = decide(v0)
    assert decision.passed is False
    assert any("decision accuracy" in reason for reason in decision.reasons)


def test_promote_blocks_when_the_baseline_is_missing(auth_header: dict[str, str], tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        tool_transport="inprocess",
        planner="keyword",
        baseline_path=tmp_path / "missing.json",
    )
    application = create_app(
        settings,
        client=InProcessToolClient(tmp_path),
        retriever=memory_retriever(),
        database_probe=StaticProbe(False),
    )
    with TestClient(application) as client:
        blocked = client.post(
            "/v1/runs",
            headers=auth_header,
            json={"query": "forge planner worker critic", "mode": "prod"},
        )
        metrics = client.get("/v1/metrics", headers=auth_header)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["reasons"] == ["no measured baseline"]
    assert metrics.json()["status"] == "not_measured"


def test_promote_blocks_on_the_v0_baseline(auth_header: dict[str, str], tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        tool_transport="inprocess",
        planner="keyword",
        baseline_path=CURRENT_BASELINE.parent / "v0.json",
    )
    application = create_app(
        settings,
        client=InProcessToolClient(tmp_path),
        retriever=memory_retriever(),
        database_probe=StaticProbe(False),
    )
    with TestClient(application) as client:
        blocked = client.post(
            "/v1/runs",
            headers=auth_header,
            json={"query": "forge planner worker critic", "mode": "prod"},
        )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["faithfulness"] == 0.8136
