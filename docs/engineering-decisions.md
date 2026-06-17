# Engineering Decisions

## 3 major decisions

### 1. Parallel + adaptive LangGraph workflow (not a linear pipeline)
**Decision.** Fan out research into four specialized branches (website, news, funding/signals,
competitors), merge, analyze into **grounded sections**, then run an **LLM-as-judge** that can loop
back through an **adaptive re-plan** targeting only weak sections, followed by a self-healing
**Unknowns Resolver**.

**Alternatives considered.**
- *Single linear chain* (planner→research→analyze→report): simplest, but it's effectively a prompt
  pipeline and doesn't justify LangGraph.
- *One big agent with tools (ReAct)*: flexible but non-deterministic, hard to show progress, harder
  to make recoverable and observable.

**Tradeoffs.** More nodes and more LLM/search calls (higher cost/latency) in exchange for parallelism,
genuine agentic behavior (it reacts to weak grounding), determinism, and clean per-node progress +
metrics. Mitigated with caching, per-node timeouts/degradation, and a bounded retry count.

### 2. Bring-Your-Own-Key with keys in request headers (provider-agnostic)
**Decision.** The user picks the provider/model and supplies keys in the UI; the frontend sends them
as headers via `fetch-event-source`; the backend builds a fresh client per request and never persists
or logs them.

**Alternatives considered.**
- *Server-side env keys*: simplest, but ties the demo to our billing and hides the provider-abstraction skill.
- *Keys as SSE query params*: the native `EventSource` can't set headers, so this was the easy path —
  but it leaks secrets into URLs/logs. Rejected; we used `fetch-event-source` to keep keys in headers instead.

**Tradeoffs.** A bit more frontend plumbing (custom SSE client) and a provider factory, in exchange
for flexibility, a clean security story, and no vendor lock-in.

### 3. SQLite + sync SQLAlchemy for app data; AsyncSqliteSaver for graph checkpoints
**Decision.** Use sync SQLAlchemy for sessions/events/messages/cache (short, self-contained calls)
and LangGraph's `AsyncSqliteSaver` for checkpoints, opened once in the app lifespan.

**Alternatives considered.**
- *Postgres + async SQLAlchemy*: production-grade, but heavier to stand up for a 1-command demo.
- *In-memory state*: trivial, but loses persistence and recoverability (both graded requirements).

**Tradeoffs.** Sync DB calls inside async handlers can technically block the loop; for SQLite-scale
local usage the calls are sub-millisecond and the simplicity is worth it. The DB layer is isolated
behind a repository, so swapping to async Postgres later is localized.

## Top technical-debt items
1. **Sync DB in async paths** — fine at this scale; should move to async SQLAlchemy / a threadpool for production.
2. **Cache has no TTL/invalidation** — a stale company report persists until the `cache` table is cleared.
3. **No automated tests yet** — needs unit tests for nodes (mocked LLM/Tavily) and an API contract test.
4. **Prompts are static strings** — versioned but not A/B-testable or eval-backed.
5. **Frontend lacks a global toast/error boundary** — errors are surfaced per-view, not centrally.

## Biggest technical risk
**LLM structured-output reliability across providers.** The graph depends on `with_structured_output`
returning schema-valid objects at several nodes. A provider/model that returns malformed output (or
times out) can fail `analyze`/`report`. Mitigated by `include_raw` parsing with explicit errors,
client-level `max_retries`, graceful degradation on research branches, and the bounded quality loop —
but a hard parse failure on a core node still fails the run. Next step: add a repair/retry wrapper
that re-asks with the validation error.

## What we'd improve with 2 extra weeks
- **Eval harness** for report quality + confidence calibration (golden companies, scored rubrics).
- **Async Postgres** + Alembic migrations; connection pooling.
- **Cache TTL + manual "force refresh"**, and de-dup of near-identical sources semantically.
- **Structured-output repair loop** and per-node circuit breakers.
- **Tests + CI** (unit for nodes with mocked deps, contract tests for the SSE endpoints).
- **Multi-run comparison** (diff a company over time) and a monitoring agent.
