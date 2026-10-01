import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sdk"))
os.environ["COSIGNAL_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from cosignal import Cosignal  # noqa: E402
from server import risk, scoring  # noqa: E402
from server.app import app  # noqa: E402

client = TestClient(app)


def test_payment_policies():
    assert risk.decide("create_payment", {"amount": 12_400})["action"] == "require_approval"
    assert risk.decide("create_payment", {"amount": 7_000})["action"] == "flag"
    assert risk.decide("create_payment", {"amount": 900})["action"] == "allow"


def test_email_policies():
    assert risk.decide("send_email", {"to": "ap-team@acme.com"})["action"] == "allow"
    assert risk.decide("send_email", {"to": "someone@gmail.com"})["policies"] == ["external-email"]


def test_reliability_score_bounds():
    runs = [{"status": "success", "steps": [{}] * 4, "risky": 0, "duration": 5000, "cost": 0.02} for _ in range(10)]
    assert scoring.reliability(runs, 10_000)["score"] == 100
    runs[0]["status"] = "failed"
    assert scoring.reliability(runs, 10_000)["score"] == 95


def test_ingest_enriches_cost_and_flags():
    body = {"id": "run_t1", "agent": "invoice-processor", "started_at": 1_700_000_000_000, "steps": [
        {"kind": "llm", "name": "extract", "model": "gpt-4o", "tokens_in": 10_000, "tokens_out": 1_000, "dur": 2000},
        {"kind": "action", "name": "create_payment", "amount": 8_000, "dur": 500}]}
    r = client.post("/v1/runs", json=body)
    assert r.status_code == 201
    run = client.get("/v1/runs/run_t1").json()
    assert abs(run["cost"] - 0.035) < 1e-9          # 10k x $2.50/M + 1k x $10/M
    assert run["steps"][1]["flags"] == ["payment-review"] and run["risky"] == 1
    assert run["duration"] == 2500 and run["steps"][1]["start"] == 2000


def test_check_endpoint():
    r = client.post("/v1/check", json={"agent": "invoice-processor", "action": "create_payment", "payload": {"amount": 20_000}})
    assert r.json()["action"] == "require_approval"


def test_sdk_buffers_when_server_is_down(tmp_path):
    buf = tmp_path / "buf.jsonl"
    lens = Cosignal(agent="x", api_url="http://127.0.0.1:9", buffer_path=str(buf), timeout=0.5)
    with lens.run(input="hello") as run:
        with run.step("tool", "noop") as s:
            s.output("ok")
    assert buf.exists() and buf.read_text().count("\n") == 1


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def test_sdk_end_to_end_with_guardrail():
    import uvicorn
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    lens = Cosignal(agent="invoice-processor", api_url=f"http://127.0.0.1:{port}")
    with lens.run(input="big invoice", run_id="run_e2e") as run:
        with run.step("llm", "extract", model="gpt-4o-mini") as s:
            s.tokens(1000, 100)
        decision = run.check("create_payment", amount=15_000)
        assert not decision.allowed and decision.action == "require_approval"
    stored = client.get("/v1/runs/run_e2e").json()
    assert stored["status"] == "blocked" and "High-value payment" in stored["fail"]
    server.should_exit = True


def test_rules_file_drives_decisions(tmp_path):
    custom = tmp_path / "p.yaml"
    custom.write_text("company_domain: acme.com\nrules:\n  - {id: tiny, name: Tiny limit, actions: [create_payment], when: [{field: amount, op: gt, value: 100}], decision: block, severity: high}\n")
    risk.reload(str(custom))
    try:
        assert risk.decide("create_payment", {"amount": 500})["action"] == "block"
        assert risk.decide("create_payment", {"amount": 50})["action"] == "allow"
    finally:
        risk.reload()


def test_new_payee_needs_approval():
    assert risk.decide("create_payment", {"amount": 200, "new_payee": True})["action"] == "require_approval"


def test_approval_inbox_flow():
    r = client.post("/v1/check", json={"agent": "invoice-processor", "run_id": "run_ap1", "action": "create_payment", "payload": {"amount": 25_000}})
    aid = r.json()["approval_id"]
    assert any(a["id"] == aid for a in client.get("/v1/approvals?status=pending").json())
    done = client.post(f"/v1/approvals/{aid}/decision", json={"decision": "approve", "by": "maria", "note": "ok"}).json()
    assert done["status"] == "approved" and done["decided_by"] == "maria"
    assert client.post(f"/v1/approvals/{aid}/decision", json={"decision": "reject"}).status_code == 409
    kinds = [(e["kind"], e["decision"]) for e in client.get("/v1/audit").json()]
    assert ("approval", "approved") in kinds and ("check", "require_approval") in kinds


def test_sdk_waits_for_human_approval():
    import uvicorn
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)

    def reviewer():   # a human approves a few seconds later
        for _ in range(40):
            pend = client.get("/v1/approvals?status=pending").json()
            mine = [a for a in pend if a["run_id"] == "run_wait"]
            if mine:
                client.post(f"/v1/approvals/{mine[0]['id']}/decision", json={"decision": "approve", "by": "dev"})
                return
            time.sleep(0.1)
    threading.Thread(target=reviewer, daemon=True).start()
    lens = Cosignal(agent="invoice-processor", api_url=f"http://127.0.0.1:{port}")
    with lens.run(input="large invoice", run_id="run_wait") as run:
        d = run.check("create_payment", amount=18_000, wait=10)
        assert d.allowed and d.action == "approved" and d.decided_by == "dev"
    assert client.get("/v1/runs/run_wait").json()["status"] == "success"
    server.should_exit = True
