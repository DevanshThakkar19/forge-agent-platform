from fastapi.testclient import TestClient
from tests.conftest import StaticProbe, memory_retriever
from tests.samples import HAPPY_QUERY

from app.config import Settings
from app.main import create_app


def test_request_path_uses_stdio_servers(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        api_key="test-key",
        sandbox_root=tmp_path,
        tool_transport="stdio",
        planner="keyword",
    )
    application = create_app(
        settings,
        retriever=memory_retriever(),
        database_probe=StaticProbe(False),
    )
    with TestClient(application) as client:
        response = client.post(
            "/v1/runs",
            headers={"X-API-Key": "test-key"},
            json={"query": HAPPY_QUERY},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["accepted"] is True
    assert [item["tool"] for item in body["result"]["tool_calls_summary"]] == [
        "retrieve",
        "web_search",
        "sql_query",
        "http_get",
        "write_file",
    ]
    assert all(item["ok"] for item in body["result"]["tool_calls_summary"])
    note = tmp_path / "notes" / "run.txt"
    assert note.is_file()
    assert "order 1001" in note.read_text(encoding="utf-8")
