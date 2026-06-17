"""Node instrumentation + structured-output helper.

`instrument` wraps every graph node to record duration and token usage, and to
emit a uniform progress event into shared state (`events`). `invoke_structured`
runs an LLM with structured output while capturing token usage via a contextvar.
"""
import contextvars
import time
from functools import wraps

from app.logging_config import get_logger

log = get_logger("graph.node")

# Per-node (per-async-task) token accumulator. Parallel branches each get their
# own copy because contextvars are copied when a new task is spawned.
_tokens: contextvars.ContextVar[int] = contextvars.ContextVar("node_tokens", default=0)


def add_tokens(n: int) -> None:
    try:
        _tokens.set(_tokens.get() + int(n or 0))
    except Exception:
        pass


async def invoke_structured(llm, schema, prompt):
    """Invoke an LLM with structured output, capturing token usage."""
    structured = llm.with_structured_output(schema, include_raw=True)
    result = await structured.ainvoke(prompt)

    raw = result.get("raw") if isinstance(result, dict) else None
    parsed = result.get("parsed") if isinstance(result, dict) else result
    if raw is not None:
        usage = getattr(raw, "usage_metadata", None) or {}
        add_tokens(usage.get("total_tokens", 0))
    if parsed is None:
        err = result.get("parsing_error") if isinstance(result, dict) else None
        raise ValueError(f"structured output parse failed: {err}")
    return parsed


def instrument(node_name: str, degrade: bool = False):
    """Decorator for graph nodes.

    Records duration_ms + tokens and appends a progress event to state.
    If `degrade` is True, a raised exception is swallowed into a 'degraded' event
    so the run continues; otherwise the exception propagates (run fails).
    """

    def decorator(fn):
        @wraps(fn)
        async def wrapper(state, config=None):
            _tokens.set(0)
            t0 = time.perf_counter()
            try:
                result = await fn(state, config) or {}
                status, message = "success", result.pop("_message", node_name)
            except Exception as exc:
                if not degrade:
                    log.exception("node %s failed", node_name)
                    raise
                log.warning("node %s degraded: %s", node_name, exc)
                result = {"errors": [f"{node_name}: {exc}"]}
                status, message = "degraded", f"{node_name} degraded: {exc}"

            duration_ms = int((time.perf_counter() - t0) * 1000)
            tokens = _tokens.get()
            event = {
                "node": node_name,
                "status": status,
                "message": message,
                "duration_ms": duration_ms,
                "tokens": tokens,
            }
            result["events"] = result.get("events", []) + [event]
            return result

        return wrapper

    return decorator
