"""Gap-research node — runs the targeted queries produced by Re-Plan, appending
to the shared research channels, then loops back to Merge → Analyze."""
import asyncio

from app.graph.instrument import instrument


@instrument("gap_research", degrade=True)
async def gap_research_node(state, config):
    tavily = config["configurable"]["tavily"]
    queries = state.get("next_queries", []) or []
    if not queries:
        return {"next_queries": [], "_message": "No gap queries to run"}

    results = await asyncio.gather(*[tavily.search(q) for q in queries])
    raw, sources = [], []
    for q, res in zip(queries, results):
        raw.append({"query": q, "results": res})
        for r in res:
            if r.get("url"):
                sources.append({"title": r.get("title", ""), "url": r["url"]})
    return {
        "raw_results": raw,
        "sources": sources,
        "next_queries": [],  # consumed
        "_message": f"Ran {len(queries)} targeted gap queries",
    }
