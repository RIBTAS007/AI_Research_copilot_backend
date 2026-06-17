"""Tavily search client wrapper: async-friendly + cache-backed + fail-soft."""
import asyncio

from app.graph import cache
from app.logging_config import get_logger

log = get_logger("graph.tavily")


class TavilyService:
    def __init__(self, api_key: str):
        from tavily import TavilyClient

        self._client = TavilyClient(api_key=api_key)

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Return a list of {title, url, content}. Cached by query; never raises."""
        key = cache.search_key(query)
        cached = cache.get(key)
        if cached is not None:
            return cached.get("results", [])

        try:
            raw = await asyncio.to_thread(
                self._client.search,
                query=query,
                max_results=max_results,
                search_depth="advanced",
            )
        except Exception as exc:  # fail soft — a dead query must not kill the run
            log.warning("tavily search failed for %r: %s", query, exc)
            return []

        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            }
            for r in raw.get("results", [])
        ]
        cache.set(key, {"results": results})
        return results
