# Cosignal: human approval and an audit trail for AI agents that move money

## The problem

Companies are moving AI agents from pilots into real workflows: agents that process invoices, answer customers, research leads and onboard employees. Once an agent acts on its own, three questions land on a manager's desk that today's tools answer poorly:

1. **What did the agent actually do?** When an invoice is paid twice or a customer gets a wrong answer, nobody can replay the agent's steps.
2. **What is it costing us?** Model and tool spend drifts upward quietly, run by run.
3. **Is it doing anything risky?** Agents can send external emails, touch customer data or trigger payments, often with no record of who approved it.

Existing tracing tools are built for the engineers who write agents. The people accountable for the agent's outcomes (operations leads, finance controllers, compliance and IT risk) have no view of their own.

## The product

Cosignal records every step of every agent run, turns that record into business-level reliability, cost and risk signals, and enforces simple guardrails before risky actions happen.

| Layer | What it does |
|---|---|
| **Record** | A lightweight Python SDK (two lines to add) captures each step: model calls, tool calls, data lookups and actions, with timing, tokens, cost and errors. |
| **Replay** | Any run can be replayed step by step on a timeline, like a flight recorder after an incident. |
| **Score** | Each agent gets a 0–100 reliability score combining success rate, policy violations, latency and cost stability. |
| **Guard** | Policies such as "payments above $10,000 need human approval" or "flag any external email" are checked *before* the action runs, and every decision is logged as an audit trail. |
| **Alert** | Plain-language alerts: "Invoice agent failures up 14% this week; spend up $120." |

## Who it is for

- **Buyer:** Head of Operations or Finance, or the IT/risk lead responsible for AI governance, at companies with 3–50 agents in production.
- **Daily users:** the ops managers who own each agent's workflow, plus the engineers who fix failures.
- **First market:** mid-size companies in finance-heavy workflows (accounts payable, customer support, sales ops), where a wrong action has a clear dollar cost.

## Why it scales

- **Framework-agnostic:** the SDK wraps any Python agent (custom code, LangChain, CrewAI, OpenAI Agents). It works with any model provider.
- **Multi-tenant by design:** every run is tagged with a workspace and agent, so one deployment serves many customers.
- **Policies as data:** new guardrails are configuration, not code, so the product grows with each customer's rules.
- **Usage-based pricing** aligns revenue with customer adoption (see below).

## MVP scope (built for the demo)

- Python SDK: `run()` and `step()` context managers, a `@traced` decorator, cost calculation, offline buffering, and a `check()` call for pre-action guardrails.
- FastAPI backend with SQLite (swap to Postgres for production): ingest runs, list and fetch runs, per-agent summaries, alerts, policy checks.
- Risk engine with four starter policies: high-value payment, external email, customer PII access, and runaway cost per run.
- Dashboard: overview KPIs, spend trend, alerts, agent reliability table, failure causes, run explorer with step-by-step replay, and a policies view.
- Simulator that generates realistic runs for four sample agents.

## Reliability score

`score = 100 × (0.50 × success rate + 0.20 × (1 − risky-step rate) + 0.15 × latency score + 0.15 × cost stability)`

- **Latency score:** 1.0 when p95 latency is under the agent's target, falling linearly to 0 at 3× the target.
- **Cost stability:** 1 − (coefficient of variation of cost per run), floored at 0.

Weights are deliberately simple so a manager can explain the score; customers can tune them per agent later.

## Architecture

```
Agent code ──(Cosignal SDK)──► Ingest API (FastAPI) ──► Store (SQLite → Postgres)
     │                               │                        │
     └─── check() before risky ──►  Risk engine (policies)    └──► Summaries, alerts, scores
          actions                                                        │
                                                            Dashboard (web) ◄──┘
```

Production path: move ingest behind a queue (e.g. Azure Service Bus), store traces in Postgres with object storage for large payloads, and compute summaries on a schedule (Databricks or a small worker).

## Pricing hypothesis

| Plan | For | Price |
|---|---|---|
| Starter | 1–3 agents, 10K steps/month | $49/month |
| Team | Up to 20 agents, 250K steps, policies and alerts | $399/month |
| Enterprise | Unlimited, SSO, audit export, on-premise option | Custom |

## Competitive landscape

Developer tracing and observability tools already exist for LLM apps. Cosignal positions differently: **governance and business outcomes for non-engineers** (reliability scores, cost accountability, policy enforcement and audit trails) rather than prompt debugging.

## Success metrics

- Time to first trace: under 10 minutes.
- Share of risky actions caught before execution.
- Weekly active managers per workspace (not just engineers).
- Customer-reported: incidents resolved faster, agent spend reduced.

## Roadmap

| When | Milestone |
|---|---|
| Week 1 (now) | MVP: SDK, API, risk engine, dashboard, simulator |
| Weeks 2–3 | Postgres + auth, LangChain and OpenAI Agents integrations, Slack alerts, approval workflow for blocked actions |
| Month 2 | Anomaly detection on cost and failures, evaluation sets per agent, audit export (CSV/PDF) |
| Month 3 | Pilot with 2–3 companies; measure incidents avoided and spend saved |

## 2-minute demo script

1. **Hook (15s):** "Companies are putting AI agents to work, but nobody can answer: what did it do, what did it cost, and was it safe?"
2. **Overview (30s):** show runs, success rate, spend and the reliability table. Point at the agent with the lowest score.
3. **Alert (20s):** open the invoice-agent alert and click through to a failed run.
4. **Replay (30s):** press Replay and walk the timeline step by step, stopping on the blocked $12,400 payment and its policy.
5. **Policies (15s):** show the rule that blocked it and how many times it fired this week.
6. **Close (10s):** "Two lines of code to add, and every agent becomes accountable."
