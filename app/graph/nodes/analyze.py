"""Analyze node — synthesize gathered research into grounded sections (content +
confidence + sources + missing_data per section)."""
from app.graph import prompts
from app.graph.format import results_to_blob
from app.graph.instrument import instrument, invoke_structured
from app.graph.schemas import ResearchAnalysis


@instrument("analyze")
async def analyze_node(state, config):
    llm = config["configurable"]["llm"]
    blob = results_to_blob(state.get("raw_results", []))
    prompt = prompts.analyze_prompt(
        state["company_name"], state.get("objective", ""), blob
    )
    analysis = await invoke_structured(llm, ResearchAnalysis, prompt)
    sections = analysis.model_dump()
    avg_conf = round(
        sum(s["confidence"] for s in sections.values()) / max(len(sections), 1), 2
    )
    return {
        "sections": sections,
        "_message": f"Analyzed into {len(sections)} grounded sections (avg confidence {avg_conf})",
    }
