"""Four specialized research branches that run in PARALLEL (graph fan-out).

Each branch is blind to the others and writes into the shared `raw_results` /
`sources` channels (which use operator.add, so concurrent appends are safe).
All branches are `degrade=True`: a failing branch produces partial data, never
crashes the whole run.
"""
import asyncio

from app.graph.instrument import instrument


async def _run_queries(tavily, queries: list[str]) -> dict:
    results = await asyncio.gather(*[tavily.search(q) for q in queries])
    raw, sources = [], []
    for q, res in zip(queries, results):
        raw.append({"query": q, "results": res})
        for r in res:
            if r.get("url"):
                sources.append({"title": r.get("title", ""), "url": r["url"]})
    return {"raw_results": raw, "sources": sources}


@instrument("research:website", degrade=True)
async def branch_website_node(state, config):
    tavily = config["configurable"]["tavily"]
    company, site = state["company_name"], state.get("website", "")
    queries = [
        f"{company} official website products and company overview",
        f"{site} about products services" if site else f"{company} what they do",
    ]
    out = await _run_queries(tavily, queries)
    out["_message"] = "Website & overview research complete"
    return out


@instrument("research:news", degrade=True)
async def branch_news_node(state, config):
    tavily = config["configurable"]["tavily"]
    company = state["company_name"]
    queries = [
        f"{company} latest news 2026",
        f"{company} recent announcements partnerships launches",
    ]
    out = await _run_queries(tavily, queries)
    out["_message"] = "News research complete"
    return out


@instrument("research:funding", degrade=True)
async def branch_funding_node(state, config):
    tavily = config["configurable"]["tavily"]
    company = state["company_name"]
    queries = [
        f"{company} funding revenue valuation investors",
        f"{company} hiring headcount growth signals",
    ]
    out = await _run_queries(tavily, queries)
    out["_message"] = "Funding & growth-signal research complete"
    return out


@instrument("research:competitors", degrade=True)
async def branch_competitors_node(state, config):
    tavily = config["configurable"]["tavily"]
    company = state["company_name"]
    queries = [
        f"{company} competitors and alternatives",
        f"{company} market position differentiation",
    ]
    out = await _run_queries(tavily, queries)
    out["_message"] = "Competitor research complete"
    return out
