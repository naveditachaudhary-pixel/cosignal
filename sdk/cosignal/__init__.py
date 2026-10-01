"""Cosignal SDK: record every step your AI agent takes.

Usage:
    from cosignal import Cosignal
    lens = Cosignal(agent="invoice-processor")

    with lens.run(input="invoice from Northwind") as run:
        with run.step("llm", "extract_fields", model="gpt-4o") as s:
            s.tokens(6200, 240)
            s.output('{"amount": 1200}')
        decision = run.check("create_payment", amount=12400, wait=300)  # guardrail BEFORE acting;
        if decision.allowed:                                              # waits up to 5 min for a human
            with run.step("action", "create_payment", amount=12400):
                pay(...)

Only the standard library is used, so the SDK drops into any Python agent.
"""
from __future__ import annotations

import functools
import json
import os
import time
import traceback
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

__all__ = ["Cosignal", "Decision", "PRICES"]
__version__ = "0.1.0"

# USD per 1M tokens (input, output). Override via Cosignal(prices=...).
PRICES = {"gpt-4o": (2.50, 10.00), "gpt-4o-mini": (0.15, 0.60)}


@dataclass
class Decision:
    """Result of a pre-action policy check."""
    action: str                      # "allow" | "flag" | "require_approval" | "block" | "approved" | "rejected"
    policies: list = field(default_factory=list)
    reason: str = ""
    approval_id: Optional[str] = None
    decided_by: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.action in ("allow", "flag", "approved")


class _Step:
    def __init__(self, run: "_Run", kind: str, name: str, **attrs: Any):
        self.run, self.kind, self.name, self.attrs = run, kind, name, attrs
        self.data: dict = {"kind": kind, "name": name, "status": "ok", **attrs}

    def tokens(self, tokens_in: int, tokens_out: int) -> "_Step":
        self.data["tokens_in"], self.data["tokens_out"] = int(tokens_in), int(tokens_out)
        return self

    def input(self, value: Any) -> "_Step":
        self.data["input"] = _short(value)
        return self

    def output(self, value: Any) -> "_Step":
        self.data["output"] = _short(value)
        return self

    def duration(self, ms: int) -> "_Step":
        """Set the duration explicitly (for importing historical logs or simulations)."""
        self._dur_override = int(ms)
        return self

    def __enter__(self) -> "_Step":
        self._t0 = time.perf_counter()
        self.data["start"] = round((time.time() - self.run.t0) * 1000)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.data["dur"] = getattr(self, "_dur_override", None) or round((time.perf_counter() - self._t0) * 1000)
        if exc is not None:
            self.data["status"] = "error"
            self.data["error"] = f"{exc_type.__name__}: {exc}"
        model = self.data.get("model")
        if model and "tokens_in" in self.data:
            pin, pout = self.run.lens.prices.get(model, (0.0, 0.0))
            self.data["cost"] = (self.data["tokens_in"] * pin + self.data.get("tokens_out", 0) * pout) / 1e6
        self.run.steps.append(self.data)
        return False  # never swallow the agent's exceptions


class _Run:
    def __init__(self, lens: "Cosignal", input: Any = None, run_id: Optional[str] = None,
                 started_at: Optional[float] = None, **meta: Any):
        self.lens, self.meta, self._started_at = lens, meta, started_at
        self.id = run_id or "run_" + uuid.uuid4().hex[:10]
        self.input = _short(input)
        self.steps: list = []
        self.status, self.fail, self.output = "success", None, None

    def step(self, kind: str, name: str, **attrs: Any) -> _Step:
        """kind: 'llm' | 'tool' | 'retrieval' | 'action'"""
        return _Step(self, kind, name, **attrs)

    def check(self, action: str, wait: float = 0, **payload: Any) -> Decision:
        """Ask Cosignal whether a risky action may run.

        If a rule requires approval, a request appears in the dashboard's Approvals inbox (and Slack, if set up).
        With wait=seconds the agent pauses until a human approves or rejects, or the time runs out.
        Fails open (allow) if the server is unreachable, unless Cosignal(fail_closed=True)."""
        body = {"agent": self.lens.agent, "run_id": self.id, "workspace": self.lens.workspace, "action": action, "payload": payload}
        if self._started_at is not None:
            body["ts"] = round(self._started_at)
        try:
            res = self.lens._post("/v1/check", body)
            d = Decision(res.get("action", "allow"), res.get("policies", []), res.get("reason", ""), res.get("approval_id"))
        except Exception as e:  # noqa: BLE001
            d = Decision("block" if self.lens.fail_closed else "allow", [], f"policy service unavailable: {e}")
        if d.action == "require_approval" and d.approval_id and wait > 0:
            d = self.lens.wait_for_approval(d, wait)
        if not d.allowed:
            self.status, self.fail = "blocked", d.reason or f"{action} {d.action}"
            # record the stopped action on the timeline so the audit trail shows exactly what was held
            self.steps.append({"kind": "action", "name": action, "status": "held", "dur": 1,
                               "input": _short(payload), "output": f"{d.action}: {d.reason}",
                               **{k: v for k, v in payload.items() if k in ("amount", "to", "pii")}})
        return d

    def __enter__(self) -> "_Run":
        self.t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is not None:
            self.status, self.fail = "failed", f"{exc_type.__name__}: {exc}"
        elif any(s.get("status") == "error" for s in self.steps) and self.status == "success":
            self.status = "failed"
            self.fail = next(s.get("error") for s in self.steps if s.get("status") == "error")
        self.lens._send({
            "id": self.id, "agent": self.lens.agent, "workspace": self.lens.workspace,
            "started_at": round(self._started_at if self._started_at is not None else self.t0 * 1000), "status": self.status, "fail": self.fail,
            "input": self.input, "output": _short(self.output), "meta": self.meta, "steps": self.steps,
        })
        return False


class Cosignal:
    def __init__(self, agent: str, api_url: Optional[str] = None, api_key: Optional[str] = None,
                 workspace: str = "default", prices: Optional[dict] = None, fail_closed: bool = False,
                 buffer_path: str = ".cosignal_buffer.jsonl", timeout: float = 3.0):
        self.agent, self.workspace = agent, workspace
        self.api_url = (api_url or os.getenv("COSIGNAL_URL", "http://localhost:8000")).rstrip("/")
        self.api_key = api_key or os.getenv("COSIGNAL_KEY", "")
        self.prices = {**PRICES, **(prices or {})}
        self.fail_closed, self.buffer_path, self.timeout = fail_closed, buffer_path, timeout

    def run(self, input: Any = None, started_at: Optional[float] = None, **meta: Any) -> _Run:
        """Start recording a run. `started_at` (epoch ms) lets you backfill historical runs."""
        return _Run(self, input=input, started_at=started_at, **meta)

    def traced(self, kind: str = "tool", name: Optional[str] = None) -> Callable:
        """Decorator: record a function call as a step of the current run (pass `run=` when calling)."""
        def deco(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(*args, run: Optional[_Run] = None, **kwargs):
                if run is None:
                    return fn(*args, **kwargs)
                with run.step(kind, name or fn.__name__) as s:
                    s.input({"args": args, "kwargs": kwargs})
                    out = fn(*args, **kwargs)
                    s.output(out)
                    return out
            return wrapper
        return deco

    # ---- transport ----
    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(self.api_url + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "X-Cosignal-Key": self.api_key})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read() or b"{}")

    def _send(self, run: dict) -> None:
        try:
            self.flush()
            self._post("/v1/runs", run)
        except Exception:  # noqa: BLE001  keep the agent running; retry later
            with open(self.buffer_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(run) + "\n")

    def wait_for_approval(self, decision: Decision, timeout: float, poll: float = 1.0) -> Decision:
        """Poll until a human approves/rejects the held action, or `timeout` seconds pass."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                a = self._get(f"/v1/approvals/{decision.approval_id}")
                if a.get("status") in ("approved", "rejected"):
                    return Decision(a["status"], decision.policies, a.get("note") or decision.reason,
                                    decision.approval_id, a.get("decided_by"))
            except Exception:  # noqa: BLE001
                pass
            time.sleep(poll)
        return decision

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(self.api_url + path, headers={"X-Cosignal-Key": self.api_key})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read() or b"{}")

    def flush(self) -> int:
        """Send any runs buffered while the server was unreachable. Returns how many were sent."""
        if not os.path.exists(self.buffer_path):
            return 0
        with open(self.buffer_path, encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        sent = 0
        for line in lines:
            try:
                self._post("/v1/runs", json.loads(line))
                sent += 1
            except Exception:  # noqa: BLE001
                break
        remaining = lines[sent:]
        if remaining:
            with open(self.buffer_path, "w", encoding="utf-8") as f:
                f.writelines(remaining)
        else:
            os.remove(self.buffer_path)
        return sent


def _short(value: Any, limit: int = 4000) -> Optional[str]:
    if value is None:
        return None
    s = value if isinstance(value, str) else json.dumps(value, default=str)
    return s if len(s) <= limit else s[:limit] + "…"
