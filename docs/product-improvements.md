# Product & Business Thinking

## 1. Five weaknesses in the current product
1. **Static, one-shot reports** — a briefing is a snapshot; signals (funding, hiring, news) go stale immediately.
2. **No workflow integration** — research lives in our app, not in the CRM/inbox where sellers actually work.
3. **Single-company, single-user** — no account lists, no team sharing, no saved playbooks.
4. **Public-web ceiling** — grounded only on what Tavily can find; no first-party/CRM/intent data.
5. **Confidence is self-reported** — the model scores its own grounding; no external calibration or human verification path.

## 2. Top 3 improvements to build next (prioritized)
1. **Continuous monitoring agent** — re-run on a schedule, **diff** the signals, and alert sellers to changes (new funding, exec hire, product launch). Turns a one-shot tool into an always-on advantage.
2. **CRM + email integration** — push briefings into Salesforce/HubSpot and draft outreach in Gmail/Outlook. Meets sellers where they work → adoption.
3. **Confidence-driven human-in-the-loop** — low-confidence sections get flagged for one-click verification/fix, raising trust and creating a feedback signal for eval.

## 3. Who buys, who uses, why they pay
- **Buyer:** Sales / RevOps leadership (VP Sales, Head of SDR) with budget for sales productivity tooling.
- **User:** SDRs and AEs preparing for outbound and discovery calls.
- **Why pay:** account prep drops from ~30 min to ~2 min per account, briefings are consistent and
  sourced, and better-targeted outreach lifts reply and meeting-booked rates. ROI is a simple
  rep-hours-saved + pipeline-quality story.

## 4. Success metrics
- **Activation:** time-to-first-briefing; % of new users who run ≥3 sessions in week 1.
- **Value:** median prep time saved; % of sections rated high-confidence; sources per report.
- **Outcome:** briefing→meeting-booked conversion; reply rate on generated outreach.
- **Engagement/retention:** weekly active sellers; sessions/seller/week.
- **Economics:** LLM + search **cost per report**; cache hit-rate.

## 5. Four-week AI roadmap
- **W1 — Grounding & reliability:** structured-output repair loop, confidence calibration, cache TTL.
- **W2 — Monitoring agent:** scheduled re-runs + signal diffing + alerts.
- **W3 — Integrations:** CRM push + email draft generation in-workflow.
- **W4 — Eval & quality:** golden-set eval harness, regression gating on report quality, dashboards.

## 6. Biggest cost / scaling / reliability risks
- **Cost:** LLM tokens + Tavily calls scale linearly with runs and the retry/branch fan-out.
  *Mitigation:* caching (already in), cheaper models for non-critical nodes, batch/scheduled runs.
- **Scaling:** synchronous per-request graph execution won't fan out to thousands of concurrent runs.
  *Mitigation:* move runs to a queue/worker pool; async DB; horizontal workers.
- **Reliability:** dependence on third-party LLM/search availability and structured-output validity.
  *Mitigation:* retries, graceful degradation, checkpoint-based resume, provider fallback.

## 7. Feature to remove and why
**Free-form open chat (as the headline).** It's the least differentiated and the most token-hungry per
unit of value. Keep the **structured actions** (Expand / Challenge / Draft email) that map to real
selling tasks, and demote open chat to a secondary affordance once usage data confirms low engagement.

## 8. Feature to add and why
**Continuous monitoring agent.** It's the single biggest shift from "nice one-off tool" to
"can't-live-without workflow": recurring value, natural retention, and a defensible data moat (signal
history per account).

## 9. First 90-day roadmap
- **Days 0–30:** reliability + eval foundation; CRM read (account import); cache TTL; basic auth/workspaces.
- **Days 31–60:** monitoring agent (scheduling, diffing, alerts); CRM write-back + email drafting.
- **Days 61–90:** team features (shared lists, playbooks), confidence-driven human-in-the-loop,
  usage analytics, and a pricing/packaging experiment.

## 10. If I owned this product, what I'd change first
**Make it continuous and embedded.** The core insight is that a static briefing decays the moment
it's generated and lives outside the seller's workflow. I'd ship the **monitoring agent + CRM/email
integration** first — that converts a clever demo into a daily habit, drives retention, and builds the
account-signal-history moat that everything else (scoring, recommendations, automation) compounds on.
