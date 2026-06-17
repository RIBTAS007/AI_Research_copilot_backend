"""Re-Plan node (adaptive / agentic). Entered only when quality check fails.

Carries the targeted gap queries forward so the next research pass focuses ONLY
on the weak sections rather than blindly re-running everything."""
from app.graph import prompts
from app.graph.instrument import instrument


@instrument("replan")
async def replan_node(state, config):
    quality = state.get("quality", {})
    weak = quality.get("weak_sections", [])
    # next_queries was set by quality_check; keep it, just narrate the decision.
    queries = state.get("next_queries", [])
    return {
        "_message": prompts.replan_note(weak) + f" ({len(queries)} targeted queries)",
    }
