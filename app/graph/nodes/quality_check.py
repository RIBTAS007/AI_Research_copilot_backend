"""Quality Check node — LLM-as-judge over the grounded sections. Produces a
verdict, the weak section keys, and targeted gap queries for the adaptive loop."""
from app.config import settings
from app.graph import prompts
from app.graph.format import sections_to_blob
from app.graph.instrument import instrument, invoke_structured
from app.graph.schemas import QualityVerdict


@instrument("quality_check")
async def quality_check_node(state, config):
    llm = config["configurable"]["llm"]
    blob = sections_to_blob(state.get("sections", {}))
    verdict = await invoke_structured(
        llm, QualityVerdict, prompts.quality_prompt(state["company_name"], blob)
    )
    retries = state.get("retries", 0)
    will_retry = (not verdict.passed) and retries < settings.max_research_retries

    out = {
        "quality": verdict.model_dump(),
        "_message": (
            f"Quality score {verdict.score}/100 — "
            + ("passed" if verdict.passed else f"weak: {', '.join(verdict.weak_sections) or 'n/a'}")
        ),
    }
    if will_retry:
        out["retries"] = retries + 1
        out["next_queries"] = verdict.gap_queries[:4]
    return out
