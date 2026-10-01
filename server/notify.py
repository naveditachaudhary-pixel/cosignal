"""Notifications when an action is held for approval: Slack incoming webhook and/or any JSON webhook."""
import json
import os
import threading
import urllib.request


def _post(url, body):
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:  # noqa: BLE001  notifications must never break the agent
        pass


def approval_requested(approval):
    """Fire-and-forget: tell a human that an agent action is waiting for them."""
    base = os.getenv("COSIGNAL_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    amount = approval["payload"].get("amount")
    what = f'{approval["action"]}' + (f' ${amount:,.0f}' if isinstance(amount, (int, float)) else "")
    text = (f':hourglass: *{approval["agent"]}* wants to run *{what}* and needs approval.\n'
            f'{approval["reason"]}\nReview: {base}/#approvals')
    targets = []
    if os.getenv("COSIGNAL_SLACK_WEBHOOK"):
        targets.append((os.getenv("COSIGNAL_SLACK_WEBHOOK"), {"text": text}))
    if os.getenv("COSIGNAL_WEBHOOK_URL"):
        targets.append((os.getenv("COSIGNAL_WEBHOOK_URL"), {"event": "approval.requested", "approval": approval}))
    for url, body in targets:
        threading.Thread(target=_post, args=(url, body), daemon=True).start()
    return len(targets)
