# Backend — AI Research Copilot API

FastAPI service that runs the **LangGraph** research workflow, streams progress over **SSE**,
serves an **actionable chat**, and persists everything to SQLite. LLM/Tavily access is
**Bring-Your-Own-Key** — keys arrive per-request as headers and are never persisted or logged.

## Stack
- **FastAPI** + Uvicorn
- **LangGraph** (parallel + adaptive graph, `AsyncSqliteSaver` checkpointer)
- **LangChain** chat models (`langchain-anthropic`, `langchain-openai`)
- **Tavily** for web research
- **SQLAlchemy** + SQLite
- **sse-starlette** for streaming

## Run locally (Python 3.11+)
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- API: http://localhost:8000  · Swagger: http://localhost:8000/docs · Health: `/health`

## Run with Docker
```bash
docker build -t research-copilot-api .
docker run -p 8000:8000 -v $(pwd)/data:/app/data research-copilot-api
```
The container binds `$PORT` if set (e.g. on Railway/Render), else `8000`.

## Configuration (env vars)
All optional; defaults shown. Copy `.env.example` → `.env` to override. **No API keys here** — those are BYOK.

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `AI Research Copilot` | App title |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy DB |
| `CHECKPOINT_DB` | `./data/checkpoints.db` | LangGraph checkpointer file |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins (set to your frontend URL in prod) |
| `MAX_RESEARCH_RETRIES` | `2` | Max adaptive re-plan loops |
| `DEFAULT_ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Fallback model |
| `DEFAULT_OPENAI_MODEL` | `gpt-4o` | Fallback model |
| `LOG_LEVEL` | `INFO` | Log level |

## API
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness |
| `GET` | `/config` | Supported providers/models + prompt version |
| `POST` | `/sessions` | Create a research session |
| `GET` | `/sessions` | List sessions |
| `GET` | `/sessions/{id}` | Session detail (report, events+metrics, messages) |
| `POST` | `/sessions/{id}/run` | Run/resume workflow — **SSE** progress stream |
| `POST` | `/sessions/{id}/chat` | Actionable chat — **SSE** token stream |
| `GET` | `/sessions/{id}/messages` | Chat history |

**BYOK headers** (sent by the frontend via `fetch-event-source`):
`x-llm-provider`, `x-llm-key`, `x-llm-model`, and `x-tavily-key` (on `/run`).

## Project layout
```
app/
  main.py            FastAPI app + lifespan (DB, checkpointer, compiled graph)
  config.py          pydantic-settings configuration
  logging_config.py  logging + secret-redaction filter
  api/               routers: sessions, chat, config; deps.py (BYOK header parsing)
  db/                SQLAlchemy models, engine, repository
  graph/             the LangGraph workflow
    state.py         shared TypedDict state (operator.add channels)
    schemas.py       Pydantic structured outputs (Plan/Analysis/Verdict/Report)
    llm.py           BYOK provider factory
    tavily.py        cached Tavily client
    cache.py         search + report-draft cache
    instrument.py    per-node latency/token capture + structured-output helper
    prompts.py       all prompts + PROMPT_VERSION
    build.py         graph wiring (fan-out, merge, adaptive loop, checkpointer)
    nodes/           planner, 4 research branches, merge, analyze, quality_check,
                     replan, gap_research, unknowns_resolver, report
  services/          runner.py (SSE run + recovery), chat.py (grounded chat)
scripts/smoke_run.py end-to-end test with fake LLM/Tavily (no keys needed)
```

## The workflow (graph)
```
planner → [website ∥ news ∥ funding ∥ competitors] → merge → analyze
  → quality_check ─(weak)→ replan → gap_research → merge → analyze (loop)
  └─(passed)→ unknowns_resolver → report → END
```
Parallel specialist branches, an LLM-as-judge that adaptively re-plans only weak sections,
a self-healing unknowns resolver, per-section grounding + confidence, checkpoint-based
recoverability, and per-node latency/token observability.

## Test
```bash
source .venv/bin/activate
python scripts/smoke_run.py   # runs the full graph with fakes; asserts the adaptive loop + report
```

See repo root [`docs/architecture.md`](../docs/architecture.md) and
[`docs/engineering-decisions.md`](../docs/engineering-decisions.md) for design detail.
