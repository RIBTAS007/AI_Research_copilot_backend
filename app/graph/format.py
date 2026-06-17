"""Helpers to turn raw research / sections into prompt-friendly text + sources."""

_SECTION_LABELS = {
    "company_overview": "Company Overview",
    "products_services": "Products & Services",
    "target_customers": "Target Customers",
    "business_signals": "Business Signals",
    "risks_challenges": "Risks & Challenges",
}


def results_to_blob(raw_results: list, limit_chars: int = 12000) -> str:
    """Flatten accumulated search results into a bounded text blob for the LLM."""
    lines: list[str] = []
    for entry in raw_results or []:
        q = entry.get("query", "")
        lines.append(f"\n## Query: {q}")
        for r in entry.get("results", []):
            content = (r.get("content") or "").strip().replace("\n", " ")
            lines.append(f"- [{r.get('title','')}]({r.get('url','')}): {content[:600]}")
    blob = "\n".join(lines)
    return blob[:limit_chars] if blob else "(no findings)"


def sections_to_blob(sections: dict) -> str:
    lines: list[str] = []
    for key, label in _SECTION_LABELS.items():
        sec = (sections or {}).get(key) or {}
        lines.append(f"\n### {label} (confidence={sec.get('confidence', 0)})")
        lines.append(sec.get("content", "") or "(empty)")
        if sec.get("missing_data"):
            lines.append("Missing: " + "; ".join(sec["missing_data"]))
    return "\n".join(lines)


def dedupe_sources(sources: list) -> list:
    seen: set[str] = set()
    out: list[dict] = []
    for s in sources or []:
        url = (s.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append({"title": s.get("title", "") or url, "url": url})
    return out


def collect_unknowns(sections: dict) -> list[str]:
    out: list[str] = []
    for sec in (sections or {}).values():
        out.extend(sec.get("missing_data", []) or [])
    # de-dupe preserving order
    seen: set[str] = set()
    uniq = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def report_to_blob(report: dict) -> str:
    """Compact text rendering of a stored report for chat grounding."""
    if not report:
        return "(no report yet)"
    parts: list[str] = []
    for key, label in _SECTION_LABELS.items():
        sec = report.get(key) or {}
        parts.append(f"## {label}\n{sec.get('content','')}")
    parts.append(
        "## Suggested Discovery Questions\n"
        + "\n".join(f"- {q}" for q in report.get("suggested_discovery_questions", []))
    )
    parts.append(
        "## Suggested Outreach Strategy\n" + (report.get("suggested_outreach_strategy") or "")
    )
    parts.append("## Unknowns\n" + "\n".join(f"- {u}" for u in report.get("unknowns", [])))
    return "\n\n".join(parts)
