"""Unknowns Resolver (self-healing). After quality passes, take the top open
unknowns, run one extra targeted search per unknown, and ask the LLM to answer
them from the fresh findings. Resolved answers feed into the final report."""
import asyncio

from app.graph import prompts
from app.graph.format import collect_unknowns, results_to_blob
from app.graph.instrument import add_tokens, instrument

MAX_UNKNOWNS = 3


@instrument("unknowns_resolver", degrade=True)
async def unknowns_resolver_node(state, config):
    cfg = config["configurable"]
    llm, tavily = cfg["llm"], cfg["tavily"]
    unknowns = collect_unknowns(state.get("sections", {}))[:MAX_UNKNOWNS]
    if not unknowns:
        return {"resolved_unknowns": [], "_message": "No open unknowns to resolve"}

    company = state["company_name"]
    searches = await asyncio.gather(
        *[tavily.search(f"{company} {u}") for u in unknowns]
    )

    resolved = []
    new_sources = []
    for unknown, res in zip(unknowns, searches):
        for r in res:
            if r.get("url"):
                new_sources.append({"title": r.get("title", ""), "url": r["url"]})
        findings = results_to_blob([{"query": unknown, "results": res}], limit_chars=4000)
        msg = await llm.ainvoke(prompts.unknown_resolution_prompt(unknown, findings))
        usage = getattr(msg, "usage_metadata", None) or {}
        add_tokens(usage.get("total_tokens", 0))
        answer = (msg.content or "").strip()
        if answer and "still unknown" not in answer.lower():
            resolved.append({"unknown": unknown, "answer": answer})

    return {
        "resolved_unknowns": resolved,
        "sources": new_sources,
        "_message": f"Resolved {len(resolved)}/{len(unknowns)} unknowns",
    }
