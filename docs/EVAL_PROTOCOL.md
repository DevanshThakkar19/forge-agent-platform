# Eval protocol

Numbers in `backend/evals/baselines/` come from running `make eval`. Do not edit them by hand. Do not put them on a resume until you want to claim this exact setup.

## What is measured

- Set: `backend/evals/golden_set.jsonl`, 40 tasks, locked by SHA-256 in the baseline file.
- Runtime: in-process tools and the in-memory hybrid index. Same ranker as Postgres, not the Docker stdio path. Latency here is not a production p95.
- Clock: `time.perf_counter` around each run. p50 and p95 use nearest-rank: index `ceil(pct/100 * n) - 1`.
- Cost: `0` USD. No paid model and no paid search API. The field is an estimate of external spend.

## Task score

For an **accept** task, faithfulness is the F1 of:

- precision = cited sources that are in `allowed_sources` / all cited sources
- recall = `required_sources` that appear / all required sources

Faithfulness is 0 when the critic accepts a reject task, rejects an accept task, or skips a required tool.

For a **reject** task, faithfulness is 1 when the critic rejects and 0 when it accepts. Citation text is not scored on a reject.

Reported faithfulness is the mean of the 40 task scores.

Tool success rate is successful tool calls / all tool calls, across the set. A call counts as successful when its payload has `ok: true`.

Decision accuracy is the fraction of tasks whose accept/reject matches `expect`.

## Gate

`mode=promote` and `mode=prod` refuse to run unless the baseline file at `FORGE_BASELINE_PATH` (default `evals/baselines/current.json`) passes all of:

- faithfulness ≥ 0.80
- tool success ≥ 0.90
- decision accuracy = 1.00

A missing file fails closed. The HTTP status is 409. `mode=stub` does not check the gate.

CI runs `python -m app.evals.runner --check`, which executes the 5 tasks marked `sample` and checks that `current.json` still matches the golden file and still passes the gate. `pytest` recomputes the full set and compares the deterministic fields to `current.json`.

## What these scores are not

- Critic `confidence` (0.5 accept, 0.2 reject) is a self-score. It is not faithfulness.
- One run's `elapsed_ms` is not a percentile.
- A citation proves the retriever or a tool returned that source. The score above is whether that source was on the task's allowed list.

## v0 and v1

Both files were produced by this runner on 2026-10-21 against the same 40 tasks.

|  | v0 | v1 (`current.json`) |
| --- | --- | --- |
| Faithfulness | 0.8136 | 1.0 |
| Decision accuracy | 0.875 | 1.0 |
| Tool success | 1.0 | 1.0 |
| p50 latency | 0.533 ms | 0.558 ms |
| p95 latency | 0.801 ms | 0.892 ms |
| USD / successful task | 0 | 0 |
| Gate | fail (decision accuracy) | pass |

v1 drops citations that do not share a content token with the query, stops the orders search fixture from matching on the words `sql` and `http`, and rejects a run when a query term of 5+ characters is missing from the evidence. Notes the agent just wrote do not count as evidence. p95 did not go down. Both runs are under 1 ms because the tools are in-process fixtures.
