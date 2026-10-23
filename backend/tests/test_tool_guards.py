from pathlib import Path

from app.mcp.client import InProcessToolClient
from mcp_servers.file_store.sandbox import use_sandbox
from mcp_servers.file_store.tools import read_file, write_file
from mcp_servers.http_api.tools import http_get
from mcp_servers.sql_query.tools import sql_query
from mcp_servers.web_search.tools import web_search


def test_web_search_matches_tokens_and_empty_query() -> None:
    hit = web_search("where is order 1001")
    assert hit["ok"] is True
    assert hit["citations"][0]["source"] == "fixture://forge/orders"
    empty = web_search("   ")
    assert empty["ok"] is True
    assert empty["citations"] == []
    miss = web_search("banana")
    assert miss["citations"] == []
    generic = web_search("sql http api")
    assert generic["citations"] == []


def test_sql_query_is_read_only() -> None:
    rows = sql_query("SELECT id, status, total FROM orders")
    assert rows["ok"] is True
    assert rows["rows"][0]["id"] == 1001

    dropped = sql_query("DROP TABLE orders")
    assert dropped["ok"] is False

    multi = sql_query("SELECT id FROM orders; SELECT id FROM docs")
    assert multi["ok"] is False

    both = sql_query("SELECT * FROM orders JOIN docs")
    assert both["ok"] is False


def test_http_get_known_and_unknown_routes() -> None:
    found = http_get("/orders/1001")
    assert found["ok"] is True
    assert found["body"]["status"] == "shipped"
    missing = http_get("/admin")
    assert missing["ok"] is False
    escaped = http_get("/orders/../../etc/passwd")
    assert escaped["ok"] is False


def test_file_store_round_trip_and_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    with use_sandbox(tmp_path):
        written = write_file("notes/run.txt", "hello sandbox")
        assert written["ok"] is True
        read = read_file("notes/run.txt")
        assert read["ok"] is True
        assert read["content"] == "hello sandbox"
        escaped = write_file("../outside.txt", "nope")
        nested = write_file("notes/../../outside.txt", "nope")
    assert escaped["ok"] is False
    assert nested["ok"] is False
    assert not outside.exists()
    assert (tmp_path / "notes" / "run.txt").read_text(encoding="utf-8") == "hello sandbox"


def test_client_rejects_bad_timeout_and_unknown_tool(tmp_path: Path) -> None:
    client = InProcessToolClient(tmp_path)
    timed = client.call("web_search", "web_search", {"query": "forge"}, timeout_s=0)
    unknown = client.call("web_search", "missing", {}, timeout_s=1)
    assert timed["ok"] is False
    assert unknown["ok"] is False
