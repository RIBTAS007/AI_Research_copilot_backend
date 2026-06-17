"""Report node — assemble the final structured briefing from grounded sections,
generate the action-oriented extras (discovery questions + outreach), fold in any
resolved unknowns, and attach deduped sources + prompt version."""
from app.graph import prompts
from app.graph.format import collect_unknowns, dedupe_sources, sections_to_blob
from app.graph.instrument import instrument, invoke_structured
from app.graph.prompts import PROMPT_VERSION
from app.graph.schemas import ReportExtras


@instrument("report")
async def report_node(state, config):
    llm = config["configurable"]["llm"]
    sections = state.get("sections", {})
    blob = sections_to_blob(sections)

    extras = await invoke_structured(
        llm,
        ReportExtras,
        prompts.report_extras_prompt(state["company_name"], state.get("objective", ""), blob),
    )

    resolved = state.get("resolved_unknowns", []) or []
    resolved_set = {r["unknown"] for r in resolved}
    remaining_unknowns = [u for u in collect_unknowns(sections) if u not in resolved_set]

    report = {
        **sections,  # the 5 grounded sections
        "suggested_discovery_questions": extras.suggested_discovery_questions,
        "suggested_outreach_strategy": extras.suggested_outreach_strategy,
        "unknowns": remaining_unknowns,
        "resolved_unknowns": resolved,
        "sources": dedupe_sources(state.get("sources", [])),
        "prompt_version": PROMPT_VERSION,
    }
    return {"report": report, "_message": "Final briefing assembled"}
