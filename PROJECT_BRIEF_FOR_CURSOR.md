# Forge — Agentic Workflow Platform (MCP + Eval Gate + Deploy)

**Owner:** Devansh Thakkar · github.com/DevanshThakkar19  
**Purpose:** One heavy, production-shaped portfolio flagship for Applied AI / agents / MLOps interviews (2026).  
**This file is the single source of truth.** Paste this entire file (or `@`-mention it) into a **new Cursor chat** and say: *“Implement Forge per this brief. Start Week 1.”*

Do **not** invent metrics, employers, or domain depth. Measure everything on a golden eval set.

---

## One-liner (resume)

Production-minded multi-agent platform: MCP tool servers, hybrid RAG, eval-gated deploys, observability, FastAPI + React — Dockerized and live.

---

## Non-goals (explicit)

- No training/fine-tuning giant models from scratch  
- No computer vision / NeRF / ADAS / trading systems  
- No five parallel projects — **this repo only** until Definition of Done  
- No fake “enterprise customers” or fake production SLAs  
- No resumé lies — numbers come only from the golden set  

---

## Architecture (must match)

```
User / React UI / API key
        ↓
FastAPI (run job, get status, metrics)
        ↓
LangGraph Orchestrator: Planner → Worker(s) → Critic/Validator
        ↓                              ↓
MCP Tool Servers                 Hybrid RAG (PostgreSQL + pgvector)
(web, SQL, files, APIs)          citations + grounding
        ↓
Eval Gate (block promote if scores fail)
        ↓
Observability (traces, latency, cost, tool-fail rate)
        ↓
Docker Compose → deploy (Railway / Fly / Render)
+ GitHub Actions: lint + pytest + sample eval on PR
```

---

## Stack (lock these unless blocked)

| Layer | Choice |
|--------|--------|
| Language | Python 3.11+ |
| Agents | LangGraph + tool calling |
| Protocol | **MCP** (real servers + client), ≥4 tools |
| RAG | chunk → embed → **hybrid** (vector + keyword/BM25-ish) → cite |
| API | FastAPI + Pydantic / JSON Schema structured outputs |
| DB | PostgreSQL + **pgvector** |
| Cache (optional Week 2+) | Redis |
| Evals | Custom harness + pytest; optional Langfuse/Phoenix later |
| FE | React + TypeScript (thin but real) |
| Ops | Docker Compose, GitHub Actions CI |
| Deploy | Railway **or** Fly.io **or** Render (pick one, document it) |

---

## Repo layout (create this)

```
forge-agent-platform/
├── PROJECT_BRIEF_FOR_CURSOR.md   # this file
├── README.md                     # architecture + metrics + live URL
├── docker-compose.yml
├── .github/workflows/ci.yml
├── backend/
│   ├── pyproject.toml or requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI
│   │   ├── config.py
│   │   ├── api/                  # routes: run, status, metrics, health
│   │   ├── graph/                # LangGraph planner/worker/critic
│   │   ├── mcp/                  # MCP client + server process mgmt
│   │   ├── rag/                  # ingest, retrieve, hybrid
│   │   ├── evals/                # golden set runner + gate
│   │   └── obs/                  # tracing, latency, cost helpers
│   ├── mcp_servers/              # ≥4 MCP tool servers
│   │   ├── web_search/
│   │   ├── sql_query/
│   │   ├── file_store/
│   │   └── http_api/
│   ├── tests/
│   └── evals/
│       ├── golden_set.jsonl      # 30–50 tasks
│       └── baselines/            # store v0 vs v2 numbers
├── frontend/                     # Vite React+TS
│   ├── src/
│   │   ├── App.tsx
│   │   ├── RunView.tsx           # run + step trace + citations
│   │   └── MetricsView.tsx       # eval dashboard
│   └── package.json
└── docs/
    ├── ARCHITECTURE.md
    └── EVAL_PROTOCOL.md          # how metrics are computed
```

GitHub remote (when ready): `github.com/DevanshThakkar19/forge-agent-platform` (or ask Devansh for final name).

---

## MCP tools (minimum 4 — real servers)

1. **web_search** — search + return snippets (Tavily/Serp/Brave or mock + real key via env)  
2. **sql_query** — read-only SQL against a small demo Postgres schema  
3. **file_store** — read/write sandbox files for agent artifacts  
4. **http_api** — call a stub internal API (e.g. fake “orders” or “docs” service)

Each tool = its own MCP server process; orchestrator uses MCP client. Document env vars in `.env.example`.

---

## Agent graph (minimum behavior)

1. **Planner** — decompose user goal into steps + tool plan  
2. **Worker(s)** — execute tools / RAG retrieves with citations  
3. **Critic/Validator** — check grounding, refuse unsupported claims, request retry if needed  
4. **Structured final answer** — Pydantic schema: `answer`, `citations[]`, `tool_calls_summary`, `confidence`

Failure modes to handle explicitly: tool timeout, empty retrieval, critic reject, max-step cap.

---

## Eval gate + golden set (non-negotiable)

- **30–50** tasks in `evals/golden_set.jsonl` (fixed forever once locked)  
- Metrics (compute every run; store JSON under `evals/baselines/`):
  - Faithfulness / citation precision (define formula in `EVAL_PROTOCOL.md`)  
  - Tool success rate  
  - p50 / p95 end-to-end latency  
  - Approx `$` / successful task (token estimate OK if labeled as estimate)  
- **Eval gate:** a “prod” path or `promote` flag **fails** if faithfulness or tool-success below thresholds (document thresholds)  
- CI runs a **tiny** subset (e.g. 5 tasks) so PRs stay fast; full set is a make target / script  

**Targets (stretch, not fake):** after optimization vs v0 baseline — latency −40–60%, faithfulness ≥ ~0.8 or clear +Δ, tool success ≥ ~90%. Only claim what you measure.

---

## API surface (minimum)

- `GET /health`  
- `POST /v1/runs` — start job `{ query, mode? }`  
- `GET /v1/runs/{id}` — status, steps, citations, scores  
- `GET /v1/metrics` — latest golden / rolling stats  
- API key via header `X-API-Key` (simple)

---

## Frontend (thin but demo-ready)

- Run panel: submit query → stream or poll steps  
- Show tool calls + citations  
- Metrics page: faithfulness, latency, tool success, cost  

---

## Definition of Done (DoD) — stop when ALL true

1. `docker compose up` brings API + DB + MCP servers (+ FE)  
2. Live public URL works for a stranger  
3. ≥4 MCP tools used in a real run (visible in trace)  
4. Hybrid RAG with citations in the answer  
5. Eval gate can block a bad run  
6. Golden set documented + baseline vs improved numbers in README  
7. GitHub Actions: lint + pytest + sample eval on PR  
8. README has: architecture diagram (mermaid OK), setup, env, **live demo**, 3 metrics  

---

## 3-week plan (agent: follow in order)

### Week 1 — Skeleton that runs
- [ ] Repo scaffold + Compose (Postgres+pgvector, API)  
- [ ] FastAPI health + run/status stubs  
- [ ] LangGraph planner → worker → critic happy path  
- [ ] 4 MCP servers stubbed then wired  
- [ ] Basic RAG ingest of a small docs folder + retrieve with citations  
- [ ] pytest for graph unit + one integration test  

### Week 2 — Eval + reliability
- [ ] Golden set 30–50 tasks  
- [ ] Eval runner + `EVAL_PROTOCOL.md`  
- [ ] Eval gate on promote/prod path  
- [ ] Observability: per-run latency, tool fail rate, token/cost estimate  
- [ ] Optimize: caching, parallel tools, prompt/graph tweaks; save v0 vs v1 numbers  

### Week 3 — Productize
- [ ] React+TS UI (run + metrics)  
- [ ] CI workflow  
- [ ] Deploy live  
- [ ] README polish + mermaid architecture  
- [ ] Optional: Redis, OpenTelemetry, Langfuse  

---

## README template (fill when real)

```markdown
# Forge — Agentic Workflow Platform

Live demo: <URL>
Stack: LangGraph · MCP · pgvector · FastAPI · React · Docker

## Metrics (golden set, N=__)
| Metric | v0 | current |
|--------|----|---------|
| p95 latency | | |
| Faithfulness | | |
| Tool success | | |

## Quickstart
docker compose up --build
```

---

## Agent instructions (how to work in the other chat)

1. Read this file fully before coding.  
2. Prefer small vertical slices that run end-to-end over unfinished “frameworks.”  
3. After each milestone: update README checklist + leave a short `PROGRESS.md` (date, done, next).  
4. Secrets only in `.env` (gitignored); ship `.env.example`.  
5. Ask Devansh only when blocked on: paid API keys, deploy account, final repo name, or metric methodology disputes.  
6. Do not expand scope into CV, fine-tuning, or multi-repo monorepos.  
7. When DoD is met, stop and summarize for resume bullets (3 bullets max, with measured numbers only).  

---

## Suggested first message in the other chat

```
Implement the Forge agent platform per @forge-agent-platform/PROJECT_BRIEF_FOR_CURSOR.md.
Start Week 1 only. Create the repo scaffold, docker-compose, FastAPI health, LangGraph stub, and 4 MCP server stubs that compile. Commit-quality code; update PROGRESS.md when Week 1 slice runs.
```

---

## Resume bullets (ONLY after DoD + measured numbers)

Template — replace X/Y/Z with real figures:

- Designed **Forge**, a multi-agent platform (plan→act→validate) with **MCP tool servers**, hybrid RAG, and an **eval gate** that blocked low-faithfulness runs before promote; cut p95 latency ~X% on an N-task golden set.  
- Shipped FastAPI + React + Docker with traces for tool failures/latency/cost; CI runs pytest + eval subset on every PR.  
- Codified reusable agent patterns + structured outputs so new MCP tools plugged in without rewriting the graph; tool success ~Y%, faithfulness ~Z.

---

## Contact / identity (for README footer)

Devansh Thakkar · thakkar.devan@northeastern.edu · github.com/DevanshThakkar19  
MS AI, Northeastern (Expected December 2026)

---

*Applications chat stays separate. This brief owns the build.*
