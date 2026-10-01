"""Reliability score and alert logic, kept simple enough for a manager to explain."""
from statistics import mean, pstdev


def p95(values):
    if not values:
        return 0
    s = sorted(values)
    return s[min(len(s) - 1, int(0.95 * len(s)))]


def reliability(runs, target_ms=10_000):
    """100 x (0.5 success + 0.2 (1 - risky-step rate) + 0.15 latency + 0.15 cost stability).
    Runs held for approval count as successes: the guardrail did its job."""
    if not runs:
        return {"score": None, "runs": 0}
    n = len(runs)
    succ = sum(r["status"] != "failed" for r in runs) / n
    steps = sum(len(r["steps"]) for r in runs) or 1
    risky = sum(r["risky"] for r in runs) / steps
    lat = p95([r["duration"] for r in runs])
    lat_score = max(0.0, min(1.0, 1 - (lat - target_ms) / (2 * target_ms)))
    costs = [r["cost"] for r in runs]
    m = mean(costs)
    stab = max(0.0, 1 - (pstdev(costs) / m if m else 0))
    score = round(100 * (0.5 * succ + 0.2 * (1 - risky) + 0.15 * lat_score + 0.15 * stab))
    return {"score": score, "runs": n, "success_rate": succ, "p95_ms": lat, "spend": sum(costs),
            "avg_cost": m, "risky_step_rate": risky}


def alerts(runs_by_agent, now_ms, names=None):
    """Compare the last 24h with the previous 6 days for each agent."""
    out = []
    day = 86_400_000
    names = names or {}
    for agent, runs in runs_by_agent.items():
        label = names.get(agent, agent)
        cur = [r for r in runs if r["started_at"] > now_ms - day]
        base = [r for r in runs if now_ms - 7 * day < r["started_at"] <= now_ms - day]
        if not cur or not base:
            continue
        fc = sum(r["status"] == "failed" for r in cur) / len(cur)
        fb = sum(r["status"] == "failed" for r in base) / len(base)
        if fc - fb > 0.06:
            out.append({"agent": agent, "type": "failures", "severity": "high",
                        "title": f"{label}: failures up {round((fc - fb) * 100)} pts today",
                        "body": f"{fc:.1%} of runs failed in the last 24h vs {fb:.1%} the prior 6 days."})
        cc, cb = mean(r["cost"] for r in cur), mean(r["cost"] for r in base)
        if cb and cc / cb > 1.25:
            out.append({"agent": agent, "type": "cost", "severity": "medium",
                        "title": f"{label}: cost per run up {round((cc / cb - 1) * 100)}%",
                        "body": f"Average ${cc:.3f} per run today vs ${cb:.3f}."})
    return out
