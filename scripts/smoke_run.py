"""End-to-end smoke test with fake LLM + Tavily (no real API keys).

Exercises: parallel research branches, merge, analyze (grounded), the adaptive
quality-check loop (fail once -> replan -> gap_research -> pass), unknowns
resolver, report assembly, SSE event stream, persistence, and recovery setup.
"""
import asyncio
import os
import sys

# in-memory DB so the smoke test is isolated
os.environ["DATABASE_URL"] = "sqlite:///./data/smoke.db"
os.environ["CHECKPOINT_DB"] = "./data/smoke_ckpt.db"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import init_db  # noqa: E402
from app.db import repository  # noqa: E402
from app.graph import schemas  # noqa: E402
from app.graph.build import build_graph  # noqa: E402
from app.services import runner as runner_mod  # noqa: E402


class _Msg:
    def __init__(self, content):
        self.content = content
        self.usage_metadata = {"total_tokens": 123}


class _Structured:
    def __init__(self, schema, state):
        self.schema = schema
        self.state = state

    async def ainvoke(self, _prompt):
        s = self.schema
        if s is schemas.ResearchPlan:
            parsed = s(queries=["q1", "q2", "q3"], rationale="covers objective")
        elif s is schemas.ResearchAnalysis:
            def sec(c):
                return schemas.GroundedSection(
                    content=f"content for {c}",
                    confidence=0.8,
                    sources=["https://example.com/a"],
                    missing_data=["headcount"] if c == "business_signals" else [],
                )
            parsed = s(
                company_overview=sec("company_overview"),
                products_services=sec("products_services"),
                target_customers=sec("target_customers"),
                business_signals=sec("business_signals"),
                risks_challenges=sec("risks_challenges"),
            )
        elif s is schemas.QualityVerdict:
            self.state["qc"] += 1
            if self.state["qc"] == 1:
                parsed = s(passed=False, score=40,
                           weak_sections=["business_signals"],
                           gap_queries=["acme funding 2026"])
            else:
                parsed = s(passed=True, score=88, weak_sections=[], gap_queries=[])
        elif s is schemas.ReportExtras:
            parsed = s(
                suggested_discovery_questions=["What are your goals?", "Budget?"],
                suggested_outreach_strategy="Lead with ROI.",
            )
        else:
            raise AssertionError(f"unexpected schema {s}")
        return {"raw": _Msg("ok"), "parsed": parsed}


class FakeLLM:
    def __init__(self, state):
        self.state = state

    def with_structured_output(self, schema, include_raw=False):
        return _Structured(schema, self.state)

    async def ainvoke(self, _prompt):
        return _Msg("Resolved: ~200 employees per LinkedIn.")


class FakeTavily:
    def __init__(self, *a, **k):
        pass

    async def search(self, query, max_results=5):
        return [
            {"title": f"Result for {query}", "url": f"https://example.com/{abs(hash(query)) % 1000}",
             "content": f"Some findings about {query}."},
        ]


async def main():
    init_db()
    _qc_state = {"qc": 0}

    runner_mod.build_llm = lambda *a, **k: FakeLLM(_qc_state)
    runner_mod.TavilyService = lambda *a, **k: FakeTavily()

    graph = build_graph(None)

    session = repository.create_session("Acme Inc.", "https://acme.com", "Sell observability")
    nodes_seen = []
    report = None
    async for ev in runner_mod.run_workflow_events(
        session, provider="anthropic", llm_key="x", tavily_key="y", model=None, graph=graph
    ):
        import json
        payload = json.loads(ev["data"])
        if ev["event"] == "node":
            nodes_seen.append(payload["node"])
            print(f"  [{payload['status']:8}] {payload['node']:24} {payload['duration_ms']}ms {payload['tokens']}tok")
        elif ev["event"] == "complete":
            report = payload["report"]
        elif ev["event"] == "error":
            print("ERROR:", payload["message"])

    assert report, "no report produced"
    assert "research:website" in nodes_seen, "missing parallel branch"
    assert nodes_seen.count("analyze") >= 2, "adaptive loop did not re-run analyze"
    assert "replan" in nodes_seen, "adaptive replan did not trigger"
    assert report["company_overview"]["confidence"] == 0.8
    assert report["suggested_discovery_questions"], "missing discovery questions"
    assert report["sources"], "missing sources"
    persisted = repository.get_session(session["id"])
    assert persisted["status"] == "completed"
    assert len(persisted["events"]) == len(nodes_seen)
    print("\nNODES:", nodes_seen)
    print("OK — report sections:", [k for k in report if isinstance(report[k], dict)])
    print("OK — resolved unknowns:", report["resolved_unknowns"])
    print("SMOKE TEST PASSED ✅")


asyncio.run(main())
