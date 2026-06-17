"""All LLM prompts live here with a version stamp. The version + provider/model
used are stored on each run so reports are reproducible and debuggable."""

PROMPT_VERSION = "2026-06-17.v1"

SECTION_KEYS = [
    "company_overview",
    "products_services",
    "target_customers",
    "business_signals",
    "risks_challenges",
]


def planner_prompt(company: str, website: str, objective: str) -> str:
    return f"""You are a B2B sales research planner.

Company: {company}
Website: {website or "(none provided)"}
Sales/meeting objective: {objective or "(general background research)"}

Produce 5-8 focused web search queries that, together, will let us write a strong
sales-prep briefing covering: company overview, products & services, target customers,
business signals (funding/hiring/launches/partnerships), and risks & challenges.
Tailor the queries to the stated objective."""


def analyze_prompt(company: str, objective: str, research_blob: str) -> str:
    return f"""You are a B2B sales research analyst. Using ONLY the research findings
below, write a structured briefing about **{company}**. Objective: {objective or "general background"}.

For EACH section, also self-assess:
- confidence (0.0-1.0): how well the section is grounded in the findings.
- sources: the URLs from the findings that support the section.
- missing_data: anything important you could not determine.

Be specific and factual. Do NOT invent facts not present in the findings; if something
is unknown, say so via low confidence and missing_data rather than guessing.

=== RESEARCH FINDINGS ===
{research_blob}
=== END FINDINGS ==="""


def quality_prompt(company: str, sections_blob: str) -> str:
    return f"""You are a strict quality reviewer for sales-research briefings about {company}.

Review the draft sections below. Decide if the briefing is well-grounded and complete
enough to send to a salesperson.

Mark it as NOT passed if any core section has low confidence (< 0.5), is empty, or clearly
lacks sources. List the weak section keys and propose specific new web search queries that
would fix the weaknesses.

Section keys are: {", ".join(SECTION_KEYS)}.

=== DRAFT SECTIONS ===
{sections_blob}
=== END DRAFT ==="""


def replan_note(weak_sections: list[str]) -> str:
    return f"Re-researching weak sections: {', '.join(weak_sections) or 'general'}"


def report_extras_prompt(company: str, objective: str, sections_blob: str) -> str:
    return f"""You are a B2B sales strategist preparing someone for a meeting with **{company}**.
Objective: {objective or "general background"}.

Based on the briefing sections below, produce:
1. suggested_discovery_questions: 5-7 sharp, specific questions the seller should ask in the meeting.
2. suggested_outreach_strategy: a concise, concrete outreach approach (angle, value hypothesis, channel).

=== BRIEFING SECTIONS ===
{sections_blob}
=== END SECTIONS ==="""


def unknown_resolution_prompt(unknown: str, findings: str) -> str:
    return f"""Using only the search findings below, answer this open question as factually as
possible. If the findings do not answer it, reply exactly: "Still unknown."

Question: {unknown}

=== FINDINGS ===
{findings}
=== END FINDINGS ==="""


# --- chat -------------------------------------------------------------------

def chat_system_prompt(company: str, report_blob: str) -> str:
    return f"""You are an AI sales-research copilot. You have already produced the research
briefing below about **{company}**. Answer the user's follow-up grounded in this briefing
and the conversation. If the briefing does not contain the answer, say so honestly.

=== RESEARCH BRIEFING ===
{report_blob}
=== END BRIEFING ==="""


CHAT_ACTIONS = {
    "expand_section": (
        "Expand the section '{target}' in much greater depth. Add specifics, examples, "
        "and implications for the sales conversation."
    ),
    "challenge_insight": (
        "Critically challenge this insight: '{target}'. Identify weak grounding, counter-"
        "evidence, and what would need to be verified before relying on it."
    ),
    "generate_email": (
        "Write a concise, personalized cold outreach email to {company} tailored to the "
        "objective. Use the briefing's signals and value angle. Keep it under 150 words."
    ),
}
