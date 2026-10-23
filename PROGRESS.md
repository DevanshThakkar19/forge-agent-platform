# Progress

## 2026-10-19 — Week 1 slice runs

Scaffold, Compose, FastAPI, the LangGraph stub, and four MCP servers are in place and were executed locally.

Done:

- Repo layout with separate API, graph, schema, service, and MCP packages. Tool functions live in `mcp_servers` and are registered both on the stdio servers and in `app/mcp/registry.py`. The graph talks to them through `ToolClient`.
- `docker-compose.yml` starts Postgres with pgvector and the API. MCP servers stay stdio processes, not Compose services.
- `GET /health`, `POST /v1/runs`, `GET /v1/runs/{id}`, `GET /v1/metrics`. Metrics stay `not_measured`.
- LangGraph path: planner → worker → critic. The critic rejects empty retrieval and failed tool calls.
- Four MCP servers (`web_search`, `sql_query`, `file_store`, `http_api`) compile, register tools, and answer an MCP initialize handshake over stdio.

Verified:

- `ruff check` and `ruff format --check` clean.
- `pytest`: 19 passed.
- Local API: `GET /health` returned `mcp_servers: 4`. A four-tool run completed with `accepted: true`.
- `docker compose up --build`: `forge-api-1` and `forge-postgres-1` both became healthy. The same run through the published API completed. Containers were stopped afterward with `docker compose down`. The Postgres volume `forge_forge_pg` is still on this machine.

Not in this slice:

- The worker still calls tools in-process. Stdio is proven by tests, not used on the request path.
- No RAG index. Postgres is up in Compose and not queried. Health reports `database: configured_not_connected`.
- No golden set, no eval gate, no measured latency or faithfulness.
- No React UI and no public URL.

Next: stdio `ToolClient` on the request path, then hybrid RAG ingest with citations. That is the 2026-10-21 slice below.

## 2026-10-21 — stdio on the request path and hybrid RAG

The API now spawns the four MCP servers and calls them over stdio. Retrieval is a plan step that reads a small markdown corpus from Postgres with pgvector, fused with keyword rank, and returns citations. The planner is still keyword routing. Tool bodies are still fixtures. Confidence `0.5` / `0.2` is the critic's self-score, not a faithfulness score. Metrics stay `not_measured`.

Done:

- `StdioToolClient` is what `create_app` wires in. Tests inject `InProcessToolClient` and a memory index, so the suite does not need Docker except the Postgres integration test.
- Corpus is `backend/corpus/{overview,orders,tools}.md`. Chunks are hashed with a signed feature hash (384-d), not a neural embedder. Postgres stores them in `forge_chunks` and ranks with cosine `<=>` plus `ts_rank`. Memory search uses the same fusion. Hits with no shared tokens, or cosine below `0.2`, are dropped.
- Health reports `database: ok` when Postgres answers and `unavailable` when it does not. A down database leaves the API up and the critic rejects the run.
- Ingest skips when the corpus fingerprint and embedder id are unchanged.

Verified:

- `ruff check` and `ruff format --check` clean.
- `pytest`: 24 passed (the pgvector test included; it no longer skips when Postgres is up).
- `docker compose up --build`: `GET /health` returned `status: ok`, `database: ok`, `mcp_servers: 4`. Logs: `stdio mcp servers ready count=4` and `rag corpus indexed chunks=3`.
- `POST /v1/runs` for the order-1001 note query completed in 48 ms, `accepted: true`, with citations from `corpus/orders.md`, `corpus/tools.md`, the web fixture, the SQL fixture, the HTTP stub, and the sandbox file. Containers are still running.

Not in this slice:

- No golden set, no eval gate, no measured latency or faithfulness.
- `sql_query` still does not open Postgres. The RAG index is the only live SQL.
- No React UI and no public URL.

## 2026-10-21 — golden set and promote gate

40 tasks in `backend/evals/golden_set.jsonl`. `make eval` runs them on the in-process graph and writes `evals/baselines/`. `GET /v1/metrics` serves `current.json`. `mode=promote` and `mode=prod` return 409 unless faithfulness is at least 0.80, tool success is at least 0.90, and decision accuracy is 1.

v0, same tasks, before the grounding change: faithfulness 0.8136, decision accuracy 0.875, tool success 1.0, p95 0.801 ms. The gate fails.

v1, after dropping unsupported citations and rejecting query terms that never appear in the evidence: faithfulness 1.0, decision accuracy 1.0, tool success 1.0, p95 0.892 ms. The gate passes. External cost is estimated at 0 USD. p95 did not improve. Both clocks are the in-process runner, not Docker.

Verified:

- `ruff` clean. `pytest`: 30 passed, including a fresh 40-task run matched to `current.json`.
- Sample check: 5 tasks, faithfulness 1.0, gate true.
- A promote call against `v0.json` returns 409. A promote call against `current.json` runs.
- `order a pizza for dinner` is rejected. The order-1001 note query is still accepted.

Not in this slice:

- No React UI and no public URL. No paid API was added.

## 2026-10-21 — React UI

`frontend/` is a Vite React app with a run panel and a metrics page. Compose serves it at `http://127.0.0.1:8080` and proxies `/health` and `/v1` to the API. `make ui` is the dev server on port 5173. CI builds the frontend with `npm ci` and `npm run build`.

Verified in the browser on both the dev server and the Compose UI:

- Health reads `ok · db ok · 4 mcp`.
- The order-1001 note query is accepted and shows the five tool calls plus `corpus/orders.md`.
- `banana milkshake` is rejected with no citations.
- Metrics shows baseline v1, N=40, faithfulness 1, p95 0.892 ms, and $0.

No public URL. No paid host was created.

## 2026-10-21 — free public tunnel

`make tunnel` publishes the Compose UI. A stranger can open the current quick-tunnel URL while that process is running. Checked from outside the machine: the page returned 200, health was `ok` with the database up and 4 MCP servers, and the order-1001 note query was accepted with a `corpus/orders.md` citation.

The hostname changes every start. This is not a Fly, Render, or Railway app. GitHub CI is written and has not run, because the saved `gh` token for DevanshThakkar19 is invalid.

## 2026-10-21 — support desk UI

The page name is Forge. The frame is a support desk. Example questions only fill the box. The answer appears after Ask Forge, and the question sent is the sentence in the box. The second page is the release check. The key and the check trail stay folded.

Verified in the browser:

- Clicking "Where is order 1001?" fills the box and does not answer.
- Ask Forge then says order 1001 shipped at 42.00, and order 1002 is still processing. Sources read Order record, Order search, Orders, and Order service.
- Switching the example to "What do the docs say?" clears that answer. Ask Forge then answers from Notes and Docs service.
- Release check shows 100%, 100%, 100%, and $0 for the 40 sample questions.

## 2026-10-21 — Northline sample records

The desk now has a sample company, Northline, plus cases 4401, 4402, 4408, and 4410. Orders 1001 and 1002 stay as they were. Full pytest passed, including the golden-set check and the Postgres retrieval test. This is an indexed record book, not a trained model.

## 2026-10-21 — local model in the planner

Compose now sets `FORGE_PLANNER=local`. The planner asks the local Ollama model `mistral` which extra lookups to open. The model does not write the answer. The critic still accepts only cited evidence. If Ollama is down or the reply is not the expected JSON, the keyword list is used and the check trail says so.

The golden-set review forces the keyword planner, so the published baseline is unchanged. Health still reports `graph: stub`. It reports `planner: local` when Ollama answers `/api/tags`, and `planner: keyword` when it does not.

Verified on `http://127.0.0.1:8080` with Ollama up:

- `Read the overview` was accepted and opened the docs table and the docs route. The keyword list would not have opened those.
- `Keep Brightmill` was accepted and saved a note. The keyword list would not have saved one.
- `order a pizza` was rejected (`unsupported pizza`) even though the model opened an extra route.
- `What is case 4401?` and `Where is order 1001?` were accepted.

Pytest: 37 passed. Ruff clean. No paid model API.

## 2026-10-21 — casual questions

The local model now reads the wording before it picks lookups. Chatter is dropped. Numbers stay. A fact the person actually asked for still has to be in the records.

Verified with Ollama `mistral`:

- `What is case it about case 4401 bro dude common` was read as `What is case 4401?` and accepted.
- `so like whats going on with brightmill` was read as `Brightmill?` and accepted.
- A password question, `order a pizza bro`, and `Where is order 100 dude` were still refused.

Pytest: 41 passed. The golden-set review still uses the keyword planner.

## 2026-10-22 — public desk

The repo is [github.com/DevanshThakkar19/forge-agent-platform](https://github.com/DevanshThakkar19/forge-agent-platform). The first GitHub Actions run passed lint, the tests, the sample review, and the page build.

A Fly app was created and then destroyed the same day. A machine that stays on can be billed, and this project stays on the free path. The desk runs on this Mac. `make tunnel` is the public link, at no charge, for as long as the Mac and the tunnel process stay up.

