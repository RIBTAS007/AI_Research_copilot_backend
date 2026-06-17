"""Assemble the LangGraph workflow.

Shape (parallel + adaptive, not linear):

    START → planner ─┬─► research:website ─┐
                     ├─► research:news ─────┤
                     ├─► research:funding ──┤──► merge ─► analyze ─► quality_check ─┐
                     └─► research:competitors┘            ▲                          │
                                                          │            ┌─ replan ◄───┤ (weak)
                                          gap_research ───┘            └─► gap_research
                                                                                     │
                                quality_check ──(passed)──► unknowns_resolver ─► report ─► END
"""
from app.config import settings
from app.graph.nodes import (
    analyze_node,
    branch_competitors_node,
    branch_funding_node,
    branch_news_node,
    branch_website_node,
    gap_research_node,
    merge_node,
    planner_node,
    quality_check_node,
    replan_node,
    report_node,
    unknowns_resolver_node,
)
from app.graph.state import ResearchState

_BRANCHES = ["research_website", "research_news", "research_funding", "research_competitors"]


def route_after_quality(state) -> str:
    """Conditional edge: loop into adaptive re-plan when weak, else finalize."""
    quality = state.get("quality", {})
    retries = state.get("retries", 0)
    if not quality.get("passed", False) and retries <= settings.max_research_retries and state.get("next_queries"):
        return "replan"
    return "unknowns_resolver"


def build_graph(checkpointer=None):
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(ResearchState)

    g.add_node("planner", planner_node)
    g.add_node("research_website", branch_website_node)
    g.add_node("research_news", branch_news_node)
    g.add_node("research_funding", branch_funding_node)
    g.add_node("research_competitors", branch_competitors_node)
    g.add_node("merge", merge_node)
    g.add_node("analyze", analyze_node)
    g.add_node("quality_check", quality_check_node)
    g.add_node("replan", replan_node)
    g.add_node("gap_research", gap_research_node)
    g.add_node("unknowns_resolver", unknowns_resolver_node)
    g.add_node("report_gen", report_node)

    g.add_edge(START, "planner")
    # fan-out to parallel specialist branches
    for b in _BRANCHES:
        g.add_edge("planner", b)
        g.add_edge(b, "merge")  # fan-in: merge waits for all branches
    g.add_edge("gap_research", "merge")
    g.add_edge("merge", "analyze")
    g.add_edge("analyze", "quality_check")
    g.add_conditional_edges(
        "quality_check",
        route_after_quality,
        {"replan": "replan", "unknowns_resolver": "unknowns_resolver"},
    )
    g.add_edge("replan", "gap_research")
    g.add_edge("unknowns_resolver", "report_gen")
    g.add_edge("report_gen", END)

    return g.compile(checkpointer=checkpointer)
