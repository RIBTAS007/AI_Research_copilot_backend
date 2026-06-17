"""Application configuration via pydantic-settings.

Secrets (LLM / Tavily API keys) are intentionally absent here: they are provided
per-request by the user (BYOK) and never persisted.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Research Copilot"
    database_url: str = "sqlite:///./data/app.db"
    checkpoint_db: str = "./data/checkpoints.db"
    cors_origins: str = "*"  # allow all by default; restrict via CORS_ORIGINS env later
    max_research_retries: int = 2
    default_anthropic_model: str = "claude-sonnet-4-6"
    default_openai_model: str = "gpt-4o"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
