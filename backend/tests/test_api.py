from fastapi.testclient import TestClient
from tests.samples import HAPPY_QUERY


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["service"] == "forge-api"
    assert body["graph"] == "stub"
    assert body["database"] == "unavailable"
    assert body["mcp_servers"] == 4
    assert "postgresql" not in response.text


def test_runs_require_api_key(client: TestClient) -> None:
    missing = client.post("/v1/runs", json={"query": "forge planner"})
    wrong = client.post(
        "/v1/runs",
        headers={"X-API-Key": "nope"},
        json={"query": "forge planner"},
    )
    assert missing.status_code == 401
    assert wrong.status_code == 401


def test_metrics_publish_the_baseline(client: TestClient, auth_header: dict[str, str]) -> None:
    denied = client.get("/v1/metrics")
    assert denied.status_code == 401

    response = client.get("/v1/metrics", headers=auth_header)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "measured"
    assert body["baseline_id"] == "v2"
    assert body["tasks"] == 40
    assert body["faithfulness"] == 1.0
    assert body["decision_accuracy"] == 1.0
    assert body["tool_success_rate"] == 1.0
    assert body["estimated_cost_usd_per_success"] == 0.0
    assert body["latency_p95_ms"] == 15.744
    assert "no paid model" in body["note"]


def test_happy_path_run(client: TestClient, auth_header: dict[str, str], tmp_path) -> None:
    response = client.post("/v1/runs", headers=auth_header, json={"query": HAPPY_QUERY})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["accepted"] is True
    assert body["elapsed_ms"] >= 0
    assert [step["node"] for step in body["steps"]] == ["planner", "worker", "critic"]

    summary = body["result"]["tool_calls_summary"]
    assert [item["tool"] for item in summary] == [
        "retrieve",
        "web_search",
        "sql_query",
        "http_get",
        "write_file",
    ]
    assert all(item["ok"] for item in summary)
    assert body["result"]["confidence"] == 0.5
    assert body["tool_count"] == 5
    assert body["tool_failures"] == 0
    assert body["estimated_cost_usd"] == 0.0

    sources = {item["source"] for item in body["result"]["citations"]}
    assert "corpus/orders.md" in sources
    assert "fixture://forge/orders" in sources
    assert "sql:orders" in sources
    assert "http_api:/orders/1001" in sources
    assert "file:notes/run.txt" in sources

    note = tmp_path / "notes" / "run.txt"
    assert note.is_file()
    assert "order 1001" in note.read_text(encoding="utf-8")

    fetched = client.get(f"/v1/runs/{body['id']}", headers=auth_header)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_empty_retrieval_is_rejected(client: TestClient, auth_header: dict[str, str]) -> None:
    response = client.post(
        "/v1/runs",
        headers=auth_header,
        json={"query": "banana milkshake"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["accepted"] is False
    assert body["result"]["citations"] == []
    assert body["result"]["confidence"] == 0.2
    assert body["critic_notes"] == "rejected: empty retrieval"


def test_order_number_must_match_exactly(client: TestClient, auth_header: dict[str, str]) -> None:
    cases = [
        ("Where is order 1001?", True),
        ("Where is order 1002?", True),
        ("order 1001", True),
        ("1001", True),
        ("Is order 1002 still processing?", True),
        ("Where is order?", True),
        ("order 42", False),
        ("Where is order 42?", False),
        ("Where is order 10?", False),
        ("order 10", False),
        ("Where is order 100?", False),
        ("100", False),
        ("10000", False),
        ("Where is order 10000?", False),
        ("Where is order 1003?", False),
        ("order 10010", False),
        ("order 001001", False),
        ("order 1001 and order 9999", False),
        ("banana milkshake", False),
        ("order a pizza for dinner", False),
    ]
    for query, accepted in cases:
        response = client.post("/v1/runs", headers=auth_header, json={"query": query})
        assert response.status_code == 201, query
        body = response.json()
        assert body["accepted"] is accepted, (query, body["critic_notes"])
        if not accepted:
            assert body["critic_notes"].startswith("rejected:"), query


def test_northline_cases_are_grounded(client: TestClient, auth_header: dict[str, str]) -> None:
    brightmill = client.post(
        "/v1/runs",
        headers=auth_header,
        json={"query": "What is case 4401?"},
    )
    assert brightmill.status_code == 201
    brightmill_body = brightmill.json()
    assert brightmill_body["accepted"] is True
    assert "corpus/cases/4401.md" in {
        item["source"] for item in brightmill_body["result"]["citations"]
    }

    company = client.post(
        "/v1/runs",
        headers=auth_header,
        json={"query": "Which company is on the desk?"},
    )
    assert company.status_code == 201
    company_body = company.json()
    assert company_body["accepted"] is True
    assert "corpus/company.md" in {item["source"] for item in company_body["result"]["citations"]}

    missing = client.post(
        "/v1/runs",
        headers=auth_header,
        json={"query": "What is case 9999?"},
    )
    assert missing.status_code == 201
    assert missing.json()["accepted"] is False


def test_promote_runs_when_the_baseline_passes(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    response = client.post(
        "/v1/runs",
        headers=auth_header,
        json={"query": "banana milkshake", "mode": "promote"},
    )
    assert response.status_code == 201
    assert response.json()["accepted"] is False
    assert response.json()["mode"] == "promote"


def test_validation_and_missing_run(client: TestClient, auth_header: dict[str, str]) -> None:
    blank = client.post("/v1/runs", headers=auth_header, json={"query": "   "})
    unknown_mode = client.post(
        "/v1/runs",
        headers=auth_header,
        json={"query": "forge planner", "mode": "shadow"},
    )
    missing = client.get(
        "/v1/runs/00000000-0000-0000-0000-000000000000",
        headers=auth_header,
    )
    assert blank.status_code == 422
    assert unknown_mode.status_code == 422
    assert missing.status_code == 404
