"""Cache helpers backed by the SQLite `cache` table.

- Tavily search results are cached by hash(query) to avoid repeat paid calls.
- Report drafts are cached by hash(company + objective + prompt_version).
"""
import hashlib

from app.db import repository
from app.graph.prompts import PROMPT_VERSION


def _hash(*parts: str) -> str:
    raw = "||".join(p.strip().lower() for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def search_key(query: str) -> str:
    return "search:" + _hash(query)


def report_key(company: str, objective: str) -> str:
    return "report:" + _hash(company, objective, PROMPT_VERSION)


def get(key: str) -> dict | None:
    return repository.cache_get(key)


def set(key: str, value: dict) -> None:
    repository.cache_set(key, value)
