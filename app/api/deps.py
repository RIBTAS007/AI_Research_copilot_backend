"""Request dependencies — extract Bring-Your-Own-Key credentials from headers.

Keys travel as request headers (sent by the frontend via fetch-event-source), are
used only for the lifetime of the request, and are never persisted. The logging
redaction filter keeps them out of logs.
"""
from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass
class LLMCreds:
    provider: str
    llm_key: str
    model: str | None


@dataclass
class RunCreds(LLMCreds):
    tavily_key: str


def get_llm_creds(
    x_llm_provider: str = Header(default=""),
    x_llm_key: str = Header(default=""),
    x_llm_model: str | None = Header(default=None),
) -> LLMCreds:
    if not x_llm_provider or not x_llm_key:
        raise HTTPException(
            status_code=400,
            detail="Missing LLM credentials. Set provider + API key in Settings.",
        )
    return LLMCreds(provider=x_llm_provider, llm_key=x_llm_key, model=x_llm_model or None)


def get_run_creds(
    x_llm_provider: str = Header(default=""),
    x_llm_key: str = Header(default=""),
    x_llm_model: str | None = Header(default=None),
    x_tavily_key: str = Header(default=""),
) -> RunCreds:
    if not x_llm_provider or not x_llm_key:
        raise HTTPException(
            status_code=400,
            detail="Missing LLM credentials. Set provider + API key in Settings.",
        )
    if not x_tavily_key:
        raise HTTPException(
            status_code=400, detail="Missing Tavily API key. Set it in Settings."
        )
    return RunCreds(
        provider=x_llm_provider,
        llm_key=x_llm_key,
        model=x_llm_model or None,
        tavily_key=x_tavily_key,
    )
