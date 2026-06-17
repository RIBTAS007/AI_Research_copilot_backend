"""Pydantic schemas that structure the LLM outputs at each stage of the graph."""
from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    """Output of the Planner node."""

    queries: list[str] = Field(
        description="5-8 targeted web search queries covering the objective.",
        min_length=1,
    )
    rationale: str = Field(description="Why these queries cover the objective.")


class GroundedSection(BaseModel):
    """A single report section with grounding metadata — what separates an AI
    engineer from an API wrapper."""

    content: str = Field(description="The synthesized content for this section.")
    confidence: float = Field(
        ge=0.0, le=1.0, description="How well-grounded this section is in the sources."
    )
    sources: list[str] = Field(
        default_factory=list, description="URLs that directly support this section."
    )
    missing_data: list[str] = Field(
        default_factory=list, description="What is still unknown for this section."
    )


class ResearchAnalysis(BaseModel):
    """Output of the Analyze node — factual synthesis with per-section grounding."""

    company_overview: GroundedSection
    products_services: GroundedSection
    target_customers: GroundedSection
    business_signals: GroundedSection
    risks_challenges: GroundedSection


class QualityVerdict(BaseModel):
    """Output of the Quality Check node (LLM-as-judge)."""

    passed: bool = Field(description="True if the analysis is well-grounded and complete.")
    score: int = Field(ge=0, le=100, description="Overall quality score.")
    weak_sections: list[str] = Field(
        default_factory=list,
        description="Section keys that are weak (e.g. 'business_signals').",
    )
    gap_queries: list[str] = Field(
        default_factory=list,
        description="New search queries to fill the gaps (empty if passed).",
    )


class Source(BaseModel):
    title: str = ""
    url: str = ""


class ReportExtras(BaseModel):
    """Output of the Report node — the action-oriented parts of the briefing."""

    suggested_discovery_questions: list[str]
    suggested_outreach_strategy: str
