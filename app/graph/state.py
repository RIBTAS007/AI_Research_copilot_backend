"""Shared graph state. List channels use `operator.add` so nodes append across
parallel branches and across retry passes (e.g. research can run multiple times
via the adaptive quality-check loop)."""
import operator
from typing import Annotated, TypedDict


class ResearchState(TypedDict, total=False):
    # --- inputs ---
    company_name: str
    website: str
    objective: str

    # --- planning ---
    plan: dict
    next_queries: list[str]  # queries the next (gap) research pass should run

    # --- research (accumulate across parallel branches + retries) ---
    raw_results: Annotated[list, operator.add]
    sources: Annotated[list, operator.add]

    # --- analysis & quality ---
    sections: dict          # {section_key: GroundedSection-as-dict}
    quality: dict
    retries: int

    # --- self-healing ---
    resolved_unknowns: list  # [{unknown, answer, sources}]

    # --- output ---
    report: dict

    # --- meta (accumulate) ---
    errors: Annotated[list, operator.add]
    events: Annotated[list, operator.add]
