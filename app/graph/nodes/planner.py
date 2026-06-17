"""Planner node — turns the brief into a research strategy and dispatches branches."""
from app.graph import prompts
from app.graph.instrument import instrument, invoke_structured
from app.graph.schemas import ResearchPlan


@instrument("planner")
async def planner_node(state, config):
    llm = config["configurable"]["llm"]
    prompt = prompts.planner_prompt(
        state["company_name"], state.get("website", ""), state.get("objective", "")
    )
    plan = await invoke_structured(llm, ResearchPlan, prompt)
    return {
        "plan": plan.model_dump(),
        "retries": 0,
        "_message": f"Planned {len(plan.queries)} research directions",
    }
