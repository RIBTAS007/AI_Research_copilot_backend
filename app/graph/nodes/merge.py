"""Merge/Dedup join node — runs after the parallel branches converge.

Sources accumulate in state via operator.add; this node de-dupes them and reports
how much material was gathered. (No LLM call → zero tokens.)"""
from app.graph.format import dedupe_sources
from app.graph.instrument import instrument


@instrument("merge")
async def merge_node(state, config):
    unique = dedupe_sources(state.get("sources", []))
    n_results = sum(len(e.get("results", [])) for e in state.get("raw_results", []))
    return {
        "_message": f"Merged {n_results} results across {len(unique)} unique sources",
    }
