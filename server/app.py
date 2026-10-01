"""Cosignal API: ingest agent runs, enforce guardrails, serve summaries and the dashboard."""
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import notify, risk, scoring
from .db import Store

PRICES = {"gpt-4o": (2.50, 10.00), "gpt-4o-mini": (0.15, 0.60)}
AGENT_NAMES = {"invoice-processor": "Invoice Processor", "support-agent": "Customer Support Agent",
               "sales-research": "Sales Research Agent", "hr-onboarding": "HR Onboarding Agent"}
TARGETS = {"invoice-processor": 9000, "support-agent": 12000, "sales-research": 15000, "hr-onboarding": 10000}
DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"

app = FastAPI(title="Cosignal", version="0.1.0")
store = Store()
KEYS = {k.strip() for k in os.getenv("COSIGNAL_KEYS", "").split(",") if k.strip()}


def auth(key: Optional[str]):
    if KEYS and key not in KEYS:
        raise HTTPException(401, "Invalid or missing X-Cosignal-Key")


class StepIn(BaseModel):
    kind: str
    name: str
    status: str = "ok"
    dur: int = 0
    model: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost: Optional[float] = None
    input: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    model_config = {"extra": "allow"}   # amount, to, pii, ... are kept for policies


class RunIn(BaseModel):
    id: str
    agent: str
    workspace: str = "default"
    started_at: int
    status: str = "success"
    fail: Optional[str] = None
    input: Optional[str] = None
    output: Optional[str] = None
    meta: dict = Field(default_factory=dict)
    steps: list[StepIn] = Field(default_factory=list)


class CheckIn(BaseModel):
    agent: str
    action: str
    run_id: Optional[str] = None
    workspace: str = "default"
    ts: Optional[int] = None        # epoch ms; lets simulations and log imports backfill history
    payload: dict[str, Any] = Field(default_factory=dict)


class DecisionIn(BaseModel):
    decision: str            # "approve" | "reject"
    by: str = "reviewer"
    note: Optional[str] = None

CORE = {"kind", "name", "status", "dur", "model", "tokens_in", "tokens_out", "cost", "input", "output", "error", "i", "start", "flags"}


def enrich(run: RunIn) -> dict:
    """Compute timings, cost and policy flags so every stored run is audit-ready."""
    r = run.model_dump()
    t, cost, tokens = 0, 0.0, 0
    for i, s in enumerate(r["steps"]):
        s["i"], s["start"] = i, t
        t += s["dur"]
        if s.get("cost") is None:
            pin, pout = PRICES.get(s.get("model") or "", (0, 0))
            s["cost"] = (s["tokens_in"] * pin + s["tokens_out"] * pout) / 1e6
        cost += s["cost"]
        tokens += s["tokens_in"] + s["tokens_out"]
        payload = {k: v for k, v in s.items() if k not in CORE and v is not None}
        s["flags"] = risk.flags_for(s["name"], payload) if s["kind"] in ("action", "tool") else []
    r.update(duration=t, cost=cost, tokens=tokens)
    r["flags"] = (["runaway-cost"] if cost > risk.run_cost_limit() else []) + [f for s in r["steps"] for f in s["flags"]]
    r["risky"] = sum(any(risk.severity(f) != "low" for f in s["flags"]) for s in r["steps"]) + ("runaway-cost" in r["flags"])
    return r


@app.post("/v1/runs", status_code=201)
def ingest(run: RunIn, x_cosignal_key: Optional[str] = Header(None)):
    auth(x_cosignal_key)
    r = enrich(run)
    store.save(r)
    return {"id": r["id"], "cost": r["cost"], "flags": r["flags"], "risky": r["risky"]}


@app.post("/v1/check")
def check(body: CheckIn, x_cosignal_key: Optional[str] = Header(None)):
    """Called by the SDK before a risky action. Held actions become approval requests."""
    auth(x_cosignal_key)
    d = risk.decide(body.action, body.payload)
    if d["action"] == "require_approval":
        a = store.create_approval(body.workspace, body.run_id, body.agent, body.action, body.payload, d["policies"], d["reason"], body.ts)
        d["approval_id"] = a["id"]
        notify.approval_requested(a)
    store.audit(body.workspace, "check", body.run_id, body.agent, body.action, d["action"], "cosignal",
                {"payload": body.payload, "policies": d["policies"], "approval_id": d.get("approval_id")}, body.ts)
    return d


@app.get("/v1/approvals")
def approvals(status: Optional[str] = None, workspace: str = "default"):
    return store.list_approvals(workspace, status)


@app.get("/v1/approvals/{aid}")
def approval(aid: str):
    a = store.get_approval(aid)
    if not a:
        raise HTTPException(404, "Approval not found")
    return a


@app.post("/v1/approvals/{aid}/decision")
def decide_approval(aid: str, body: DecisionIn, x_cosignal_key: Optional[str] = Header(None)):
    """A human approves or rejects a held action. The agent (waiting in run.check) picks this up."""
    auth(x_cosignal_key)
    if body.decision not in ("approve", "reject"):
        raise HTTPException(422, "decision must be 'approve' or 'reject'")
    a = store.get_approval(aid)
    if not a:
        raise HTTPException(404, "Approval not found")
    status = "approved" if body.decision == "approve" else "rejected"
    if not store.decide_approval(aid, status, body.by, body.note):
        raise HTTPException(409, f"Already {a['status']}")
    store.audit(a["workspace"], "approval", a["run_id"], a["agent"], a["action"], status, body.by,
                {"approval_id": aid, "note": body.note, "payload": a["payload"]})
    return store.get_approval(aid)


@app.get("/v1/audit")
def audit(limit: int = 200, workspace: str = "default"):
    return store.list_audit(workspace, limit)


@app.get("/v1/runs")
def list_runs(agent: Optional[str] = None, status: Optional[str] = None, limit: int = 100, workspace: str = "default"):
    return store.query(workspace, agent, status, limit=limit)


@app.get("/v1/runs/{run_id}")
def get_run(run_id: str):
    r = store.get(run_id)
    if not r:
        raise HTTPException(404, "Run not found")
    return r


def _by_agent(runs):
    out = {}
    for r in runs:
        out.setdefault(r["agent"], []).append(r)
    return out


@app.get("/v1/agents")
def agents(days: int = 7, workspace: str = "default"):
    runs = store.query(workspace)
    if not runs:
        return []
    since = max(r["started_at"] for r in runs) - days * 86_400_000
    return [{"id": a, "name": AGENT_NAMES.get(a, a), **scoring.reliability([r for r in rs if r["started_at"] > since], TARGETS.get(a, 10_000))}
            for a, rs in _by_agent(runs).items()]


@app.get("/v1/alerts")
def get_alerts(workspace: str = "default"):
    runs = store.query(workspace)
    return scoring.alerts(_by_agent(runs), max((r["started_at"] for r in runs), default=0), AGENT_NAMES)


@app.get("/v1/policies")
def policies():
    return risk.public_rules()


@app.post("/v1/policies/reload")
def reload_policies(x_cosignal_key: Optional[str] = Header(None)):
    """Re-read policies.yaml after editing it, without restarting the server."""
    auth(x_cosignal_key)
    risk.reload()
    return risk.public_rules()


@app.get("/v1/export")
def export(workspace: str = "default", days: int = 14):
    """Everything the dashboard needs in one call (fine for MVP volumes; paginate at scale)."""
    runs = store.query(workspace)
    if runs:
        since = max(r["started_at"] for r in runs) - days * 86_400_000
        runs = [r for r in runs if r["started_at"] > since]
    agents_ = sorted({r["agent"] for r in runs})
    return {"workspace": workspace, "policies": risk.public_rules(), "runs": runs,
            "approvals": store.list_approvals(workspace), "audit": store.list_audit(workspace, 100),
            "agents": [{"id": a, "name": AGENT_NAMES.get(a, a), "target": TARGETS.get(a, 10_000)} for a in agents_]}


@app.get("/")
def dashboard():
    return FileResponse(DASHBOARD)
