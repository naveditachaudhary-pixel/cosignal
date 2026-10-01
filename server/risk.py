"""Guardrail rules engine. Rules live in policies.yaml so each company can set its own limits."""
import fnmatch
import os
from pathlib import Path

import yaml

RANK = {"allow": 0, "flag": 1, "require_approval": 2, "block": 3}
POLICY_FILE = Path(os.getenv("COSIGNAL_POLICIES", Path(__file__).resolve().parent.parent / "policies.yaml"))


def load(path=None):
    with open(path or POLICY_FILE, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    for r in cfg.get("rules", []):
        r.setdefault("on", True)
        r.setdefault("actions", ["*"])
        r.setdefault("when", [])
        r.setdefault("severity", "low")
        if r.get("decision") not in RANK:
            raise ValueError(f"rule {r.get('id')}: decision must be one of {list(RANK)}")
    return cfg


CFG = load()


def reload(path=None):
    global CFG
    CFG = load(path)
    return CFG


def company_domain():
    return os.getenv("COSIGNAL_COMPANY_DOMAIN", CFG.get("company_domain", "example.com")).lower()


def run_cost_limit():
    return float(os.getenv("COSIGNAL_RUN_COST_LIMIT", CFG.get("run_cost_limit_usd", 0.20)))


def _cond(c, payload):
    field, op, value = c.get("field"), c.get("op"), c.get("value")
    v = payload.get(field)
    if op == "exists":
        return v is not None
    if op == "email_outside":
        if not v:
            return False
        return v == "external" or not str(v).lower().endswith("@" + company_domain())
    if v is None:
        return False
    try:
        return {"gt": lambda: v > value, "gte": lambda: v >= value, "lt": lambda: v < value, "lte": lambda: v <= value,
                "eq": lambda: v == value, "ne": lambda: v != value, "in": lambda: v in value,
                "not_in": lambda: v not in value}[op]()
    except (TypeError, KeyError):
        return False


def matches(rule, action, payload):
    if not rule["on"]:
        return False
    if not any(fnmatch.fnmatch(action, pat) for pat in rule["actions"]):
        return False
    return all(_cond(c, payload) for c in rule["when"])


def flags_for(action, payload):
    """Ids of the rules an action triggers."""
    return [r["id"] for r in CFG.get("rules", []) if matches(r, action, payload)]


def decide(action, payload):
    """Pre-action check used by the SDK: the strictest matching rule wins."""
    hits = [r for r in CFG.get("rules", []) if matches(r, action, payload)]
    decision = max((r["decision"] for r in hits), key=RANK.get, default="allow")
    reason = "; ".join(f'{r["name"]}: {r.get("description", "")}' for r in hits if r["decision"] == decision)
    return {"action": decision, "policies": [r["id"] for r in hits], "reason": reason}


def severity(pid):
    if pid == "runaway-cost":
        return "medium"
    return next((r["severity"] for r in CFG.get("rules", []) if r["id"] == pid), "low")


def public_rules():
    """Rules as the dashboard shows them (plus the run-level cost rule)."""
    out = [{"id": r["id"], "name": r["name"], "rule": r.get("description", ""), "action": r["decision"],
            "severity": r["severity"], "on": r["on"]} for r in CFG.get("rules", [])]
    out.append({"id": "runaway-cost", "name": "Runaway cost", "rule": f"Single run costs more than ${run_cost_limit():.2f}",
                "action": "flag", "severity": "medium", "on": True})
    return out
