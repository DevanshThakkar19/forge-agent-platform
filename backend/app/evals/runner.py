"""Run the golden set on the in-process graph and write a baseline.

The clock is this process, not the Docker stdio path. Do not paste the
latency figures onto a resume as production p95.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.evals.gate import decide, load_baseline
from app.evals.score import aggregate, score_task
from app.evals.tasks import BASELINE_DIR, CURRENT_BASELINE, GOLDEN_PATH, golden_sha256, load_tasks
from app.mcp.client import InProcessToolClient
from app.obs.cost import COST_BASIS, ESTIMATED_USD_PER_TASK
from app.rag.corpus import load_chunks
from app.rag.memory import MemoryHybridIndex
from app.rag.retrieve import HybridRetriever
from app.schemas.runs import RunMode
from app.services.runs import RunService

RUNTIME = "inprocess+memory"


def measure(tasks: list, *, sandbox: Path) -> tuple[dict, list[dict]]:
    corpus = Path(__file__).resolve().parents[2] / "corpus"
    settings = Settings(
        _env_file=None,
        api_key="eval",
        sandbox_root=sandbox,
        corpus_dir=corpus,
        tool_transport="inprocess",
        planner="keyword",
    )
    index = MemoryHybridIndex()
    index.replace(load_chunks(corpus))
    service = RunService(
        settings,
        client=InProcessToolClient(sandbox),
        retriever=HybridRetriever(index, limit=settings.retrieve_limit),
    )
    rows: list[dict] = []
    latencies: list[float] = []
    for task in tasks:
        started = time.perf_counter()
        record = service.create(query=task.query, mode=RunMode.stub)
        elapsed_ms = (time.perf_counter() - started) * 1000
        result = record.result
        sources = [item.source for item in result.citations] if result else []
        tools = [item.model_dump() for item in result.tool_calls_summary] if result else []
        row = score_task(task, accepted=record.accepted, sources=sources, tools=tools)
        row["latency_ms"] = round(elapsed_ms, 3)
        row["critic_notes"] = record.critic_notes
        rows.append(row)
        latencies.append(elapsed_ms)
    return aggregate(rows, latencies), rows


def build_report(label: str, tasks: list) -> dict:
    with tempfile.TemporaryDirectory() as sandbox:
        summary, rows = measure(tasks, sandbox=Path(sandbox))
    decision = decide(summary)
    failures = [
        {
            "id": row["id"],
            "faithfulness": row["faithfulness"],
            "decision_ok": row["decision_ok"],
            "accepted": row["accepted"],
            "sources": row["sources"],
            "tools": row["tools"],
            "critic_notes": row["critic_notes"],
        }
        for row in rows
        if row["faithfulness"] < 1 or not row["decision_ok"]
    ]
    return {
        "id": label,
        "measured_at": datetime.now(UTC).isoformat(),
        "runtime": RUNTIME,
        "golden_sha256": golden_sha256(),
        "cost_basis": COST_BASIS,
        "estimated_cost_usd_per_success": ESTIMATED_USD_PER_TASK,
        **summary,
        "gate_passed": decision.passed,
        "gate_reasons": list(decision.reasons),
        "failures": failures,
    }


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def check_sample() -> int:
    tasks = [task for task in load_tasks() if task.sample]
    report = build_report("sample", tasks)
    baseline = load_baseline(CURRENT_BASELINE)
    decision = decide(baseline)
    problems: list[str] = []
    if not decision.passed:
        problems.extend(decision.reasons or ("baseline failed the gate",))
    for row in report["failures"]:
        if not row["decision_ok"]:
            problems.append(f"{row['id']} decision mismatch")
    if baseline and baseline.get("golden_sha256") != golden_sha256():
        problems.append("current baseline does not match the golden set hash")
    if problems:
        for problem in problems:
            print(problem)
        return 1
    print(
        f"sample ok tasks={report['tasks']} "
        f"faithfulness={report['faithfulness']} gate={decision.passed}"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure the Forge golden set")
    parser.add_argument("--label", default="v1")
    parser.add_argument("--out", type=Path, default=BASELINE_DIR / "v1.json")
    parser.add_argument("--publish", type=Path, default=None)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        raise SystemExit(check_sample())
    tasks = load_tasks(GOLDEN_PATH)
    if args.sample:
        tasks = [task for task in tasks if task.sample]
    report = build_report(args.label, tasks)
    write_report(report, args.out)
    if args.publish is not None:
        write_report(report, args.publish)
    print(
        f"wrote {args.out} tasks={report['tasks']} "
        f"faithfulness={report['faithfulness']} "
        f"tool_success={report['tool_success_rate']} "
        f"decisions={report['decision_accuracy']} "
        f"p50_ms={report['latency_p50_ms']} p95_ms={report['latency_p95_ms']} "
        f"gate={report['gate_passed']} failures={len(report['failures'])}"
    )


if __name__ == "__main__":
    main()
