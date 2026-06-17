"""Config endpoint — advertises supported providers/models to the UI."""
from fastapi import APIRouter

from app.graph.llm import SUPPORTED_PROVIDERS
from app.graph.prompts import PROMPT_VERSION

router = APIRouter()


@router.get("/config")
def get_config():
    return {
        "providers": [
            {
                "id": pid,
                "label": meta["label"],
                "models": meta["models"],
                "default_model": meta["default"],
            }
            for pid, meta in SUPPORTED_PROVIDERS.items()
        ],
        "prompt_version": PROMPT_VERSION,
        "report_sections": [
            "company_overview",
            "products_services",
            "target_customers",
            "business_signals",
            "risks_challenges",
        ],
    }
