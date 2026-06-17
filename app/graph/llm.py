"""LLM provider factory (Bring-Your-Own-Key).

The user selects a provider and supplies the API key per request, so a fresh client
is built each run. Nothing is cached or persisted.
"""
from app.config import settings

SUPPORTED_PROVIDERS = {
    "anthropic": {
        "label": "Anthropic Claude",
        "models": [
            "claude-sonnet-4-6",
            "claude-opus-4-8",
            "claude-haiku-4-5-20251001",
        ],
        "default": settings.default_anthropic_model,
    },
    "openai": {
        "label": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        "default": settings.default_openai_model,
    },
}


def build_llm(provider: str, api_key: str, model: str | None = None, temperature: float = 0.0):
    """Return a LangChain chat model for the given provider/key."""
    provider = (provider or "").lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider '{provider}'.")
    if not api_key:
        raise ValueError("Missing API key.")

    chosen = model or SUPPORTED_PROVIDERS[provider]["default"]

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=chosen,
            api_key=api_key,
            temperature=temperature,
            max_tokens=4096,
            timeout=90,
            max_retries=2,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=chosen,
        api_key=api_key,
        temperature=temperature,
        timeout=90,
        max_retries=2,
    )
