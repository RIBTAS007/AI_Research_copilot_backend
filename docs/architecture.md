# Architecture

## System overview

```
┌─────────────────────────── React SPA (Vite + TS) ───────────────────────────┐
│  Settings(BYOK)   Create Session   History   Session Detail                  │
│      │ localStorage keys                          │ SSE (fetch-event-source) │
└──────┼────────────────────────────────────────────┼─────────────────────────┘
       │ REST (+ keys as headers)                    │ progress / chat tokens
┌──────▼─────────────────────── FastAPI ─────────────▼─────────────────────────┐
│  /config   /sessions (CRUD)   /sessions/{id}/run   /sessions/{id}/chat        │
│        deps.py: extract BYOK headers (request-scoped, never persisted)        │
│  services/runner.py  ───────────────────────────────  services/chat.py        │
└──────┬──────────────────────────────────────────────────────┬────────────────┘
       │ astream(stream_mode="updates")                        │ astream tokens
┌──────▼───────────────────── LangGraph workflow ──────────────▼────────────────┐
│  planner → [website ∥ news ∥ funding ∥ competitors] → merge → analyze →        │
│  quality_check ──(weak)──► replan → gap_research ─┐                            │
│        │                                          └─► merge → analyze (loop)   │
│        └──(passed)──► unknowns_resolver → report → END                         │
│  instrument.py: per-node latency + token capture                              │
└──────┬───────────────────────────┬───────────────────────────┬────────────────┘
       │ AsyncSqliteSaver           │ BYOK LLM (Anthropic/OpenAI)│ Tavily (cached)
   checkpoints.db              langchain chat model         tavily-python
       │
┌──────▼──────────────── SQLite (SQLAlchemy) ──────────────────────────────────┐
│  sessions · workflow_events(+duration_ms,tokens) · messages · cache          │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Frontend (`frontend/src`)
- **api/client.ts** — REST helpers + SSE via `@microsoft/fetch-event-source` (lets us POST and send
  BYOK keys as headers; the native `EventSource` can't do either).
- **hooks/useSettings.ts** — BYOK settings persisted to `localStorage`.
- **pages** — Create, History, SessionDetail (orchestrates run + chat), Settings.
- **components** — `ProgressTimeline` (latency/tokens), `ReportView` (section cards, confidence
  badges, expandable sources, "Explain my report"), `ChatPanel` (streamed, actionable).

### Backend (`backend/app`)
- **api/** — routers + `deps.py` for BYOK header extraction/validation.
- **services/runner.py** — builds request-scoped LLM/Tavily clients, runs the graph via
  `astream`, emits SSE events, persists report/events, handles cache + resume.
- **services/chat.py** — report-grounded chat with action templates, token streaming.
- **graph/** — the workflow (see below).
- **db/** — SQLAlchemy models + a thin repository; each call uses its own short-lived session.

## LangGraph workflow

**State** (`graph/state.py`): a single `TypedDict`. List channels (`raw_results`, `sources`,
`errors`, `events`) use `operator.add` reducers so the **parallel branches** and **retry passes**
can append without clobbering each other.

**Nodes** (`graph/nodes/`):
1. `planner` — research strategy from {company, website, objective}.
2. `research:website|news|funding|competitors` — **four parallel specialists** (fan-out), each
   `degrade=True` (a failed branch yields partial data, never crashes the run).
3. `merge` — fan-in join: dedupes sources, no LLM (zero tokens).
4. `analyze` — synthesizes **grounded sections** (`content`, `confidence`, `sources`, `missing_data`).
5. `quality_check` — LLM-as-judge → verdict, weak sections, targeted `gap_queries`.
6. `replan` — adaptive: carries targeted gap queries (only weak sections).
7. `gap_research` — runs the gap queries, loops back into `merge → analyze`.
8. `unknowns_resolver` — self-healing extra search loop to close top unknowns.
9. `report` — assembles final briefing + discovery questions + outreach strategy.

**Routing** (`graph/build.py`): conditional edge after `quality_check` → `replan` when the verdict
fails and retries remain, else `unknowns_resolver`. Bounded by `MAX_RESEARCH_RETRIES`.

**Recoverability**: compiled with `AsyncSqliteSaver` keyed by `thread_id = session_id`. Each node
checkpoints; an interrupted run resumes from the last checkpoint on the next `/run`.

**Observability**: `graph/instrument.py` wraps every node, timing it and capturing token usage from
the LLM `usage_metadata` (via a contextvar that survives parallel task copies). Metrics are written
to `workflow_events` and streamed live.

## Data flow for one run
1. `POST /sessions` persists the session (`created`).
2. `POST /sessions/{id}/run` (SSE) → runner builds BYOK clients → `graph.astream`.
3. Each node update → `WorkflowEvent` persisted + `node` SSE event to the client.
4. On finish → report saved to `sessions.report`, status `completed`, report cached, `complete` SSE.
5. `POST /sessions/{id}/chat` → grounded, streamed answer; user/assistant messages persisted.

## Security: BYOK
Keys live only in the browser and travel as request headers used for the request lifetime. A logging
`RedactionFilter` masks key-shaped strings. Nothing key-related is written to the database.
