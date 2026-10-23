from tests.samples import HAPPY_QUERY

from app.graph.nodes.planner import NOTE_RELATIVE_PATH, build_plan


def test_happy_query_plans_retrieval_and_four_servers() -> None:
    plan = build_plan(HAPPY_QUERY, max_steps=5)
    assert [(step["server"], step["tool"]) for step in plan] == [
        ("rag", "retrieve"),
        ("web_search", "web_search"),
        ("sql_query", "sql_query"),
        ("http_api", "http_get"),
        ("file_store", "write_file"),
    ]
    assert plan[0]["kind"] == "retrieve"
    assert plan[2]["arguments"]["sql"] == "SELECT id, status, total FROM orders"
    assert plan[3]["arguments"]["path"] == "/orders/1001"
    assert plan[4]["arguments"]["path"] == NOTE_RELATIVE_PATH


def test_word_boundaries_do_not_false_trigger() -> None:
    plan = build_plan("paint the border", max_steps=4)
    assert [step["server"] for step in plan] == ["rag", "web_search"]


def test_max_steps_caps_the_plan() -> None:
    plan = build_plan(HAPPY_QUERY, max_steps=1)
    assert [step["tool"] for step in plan] == ["retrieve"]


def test_case_query_reads_the_cases_table() -> None:
    plan = build_plan("What is case 4401?", max_steps=5)
    assert plan[2]["arguments"]["sql"] == "SELECT id, status, detail FROM cases"
    assert "http_get" not in [step["tool"] for step in plan]


def test_docs_query_uses_the_docs_fixtures() -> None:
    plan = build_plan("read the docs from sql and the http api", max_steps=5)
    assert plan[2]["arguments"]["sql"] == "SELECT id, title, body FROM docs"
    assert plan[3]["arguments"]["path"] == "/docs/overview"
