"""Workflow runner: executes the LangGraph graph for a session, streams progress
events (with latency + token metrics), persists everything, and supports resume
from the checkpointer if a prior run was interrupted (recoverability)."""
import json

from app.db import repository
from app.graph.cache import report_key
from app.graph.llm import build_llm
from app.graph.prompts import PROMPT_VERSION
from app.graph.tavily import TavilyService
from app.graph import cache
from app.logging_config import get_logger

log = get_logger("services.runner")


def _sse(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


async def run_workflow_events(
    session: dict,
    *,
    provider: str,
    llm_key: str,
    tavily_key: str,
    model: str | None,
    graph,
):
    """Async generator yielding SSE events as the graph runs."""
    session_id = session["id"]
    run_meta = {"provider": provider, "model": model, "prompt_version": PROMPT_VERSION}

    # Build BYOK clients (request-scoped; never persisted).
    try:
        llm = build_llm(provider, llm_key, model)
        tavily = TavilyService(tavily_key)
    except Exception as exc:
        repository.update_status(session_id, "failed", str(exc))
        yield _sse("error", {"message": f"Setup failed: {exc}"})
        return

    config = {
        "configurable": {
            "thread_id": session_id,
            "llm": llm,
            "tavily": tavily,
        },
        "recursion_limit": 50,
    }

    inputs = {
        "company_name": session["company_name"],
        "website": session.get("website", ""),
        "objective": session.get("objective", ""),
        "retries": 0,
    }

    # Fast path: serve a cached report for the same company+objective. Only when this
    # session has no report yet (a brand-new session for an already-researched company);
    # an explicit re-run of a completed session always runs fresh.
    ckey = report_key(session["company_name"], session.get("objective", ""))
    cached = cache.get(ckey)
    if cached and not session.get("report") and session.get("status") not in ("running", "completed"):
        repository.save_report(session_id, cached["report"], run_meta)
        repository.add_event(session_id, "cache", "success", "Served report from cache", 0, 0)
        repository.update_status(session_id, "completed")
        yield _sse("start", {"session_id": session_id, "resumed": False, "cached": True})
        yield _sse("node", {"node": "cache", "status": "success", "message": "Served report from cache", "duration_ms": 0, "tokens": 0})
        yield _sse("complete", {"report": cached["report"]})
        return

    # Recoverability: resume from checkpoint if a prior run was interrupted.
    resume = False
    try:
        snapshot = await graph.aget_state(config)
        resume = bool(snapshot and snapshot.next)
    except Exception:
        resume = False

    repository.clear_events(session_id)
    repository.update_status(session_id, "running")
    yield _sse("start", {"session_id": session_id, "resumed": resume, "cached": False})

    report = None
    try:
        stream_input = None if resume else inputs
        async for chunk in graph.astream(stream_input, config=config, stream_mode="updates"):
            for node, delta in chunk.items():
                delta = delta or {}
                if delta.get("report"):
                    report = delta["report"]  # captured straight from the report node
                for ev in delta.get("events", []):
                    repository.add_event(
                        session_id,
                        ev.get("node", node),
                        ev.get("status", "success"),
                        ev.get("message", ""),
                        ev.get("duration_ms", 0),
                        ev.get("tokens", 0),
                    )
                    yield _sse("node", ev)

        if not report:
            raise RuntimeError("workflow finished without producing a report")

        repository.save_report(session_id, report, run_meta)
        repository.update_status(session_id, "completed")
        cache.set(ckey, {"report": report})
        yield _sse("complete", {"report": report})
    except Exception as exc:
        log.exception("workflow run failed for session %s", session_id)
        repository.update_status(session_id, "failed", str(exc))
        repository.add_event(session_id, "error", "failed", str(exc), 0, 0)
        yield _sse("error", {"message": str(exc)})
