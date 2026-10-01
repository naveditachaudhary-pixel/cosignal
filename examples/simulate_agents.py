"""Generate realistic agent runs through the Cosignal SDK (two weeks of history).

    python -m examples.simulate_agents --runs-per-day 40

Four sample agents: invoice processing, customer support, sales research and HR onboarding.
Each one uses the SDK exactly as a real agent would: steps, token counts, and a guardrail
check before every payment or external email.
"""
import argparse
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))
from cosignal import Cosignal  # noqa: E402

VENDORS = ["Northwind Supplies", "Contoso Metals", "Fabrikam Logistics", "Tailspin Parts", "Litware Labs"]
CUSTOMERS = ["priya", "marcus", "elena", "jordan", "aisha"]
COMPANIES = ["Brightline Health", "Keystone Freight", "Orchid Retail", "Summit Dental", "Harbor Credit Union"]


class Failure(Exception):
    pass


def invoice(lens, rnd, when, recent):
    v, amount, po = rnd.choice(VENDORS), round(math.exp(rnd.uniform(6, 9.45))), f"PO-{rnd.randint(40000, 49999)}"
    with lens.run(input=f"Invoice email from {v}", started_at=when) as run:
        with run.step("tool", "read_inbox") as s:
            s.duration(rnd.randint(250, 600)).output(f"1 invoice PDF from {v}")
        with run.step("llm", "extract_invoice_fields", model="gpt-4o") as s:
            s.tokens(rnd.randint(6000, 11000), rnd.randint(180, 320)).duration(rnd.randint(1600, 3400))
            s.input("Extract vendor, amount, PO number and due date.").output({"vendor": v, "amount": amount, "po": po})
        try:
            with run.step("tool", "lookup_vendor") as s:
                s.input(f"SELECT * FROM vendors WHERE name='{v}'")
                if rnd.random() < (0.2 if recent else 0.05):
                    s.duration(5000)
                    raise Failure("Timeout after 5000 ms: vendor_db")
                s.duration(rnd.randint(180, 700)).output("vendor verified, terms NET30")
        except Failure:
            return
        decision = run.check("create_payment", amount=amount, vendor=v, new_payee=rnd.random() < 0.03)
        if not decision.allowed:
            run.output = f"Held for approval: {decision.reason}"
            return
        with run.step("action", "create_payment", amount=amount) as s:
            s.duration(rnd.randint(300, 800)).input(f"create_payment({v}, {amount}, {po})").output("Payment scheduled")
        run.output = "Payment scheduled"


def support(lens, rnd, when, recent):
    who = rnd.choice(CUSTOMERS)
    with lens.run(input=f"Ticket from {who}", started_at=when) as run:
        with run.step("retrieval", "search_knowledge_base") as s:
            s.duration(rnd.randint(300, 900)).output("4 articles")
        with run.step("tool", "read_customer_record", pii=True) as s:
            s.duration(rnd.randint(200, 500)).output("name, email, order history")
        try:
            with run.step("llm", "draft_reply", model="gpt-4o") as s:
                s.tokens(rnd.randint(11000, 16000) if recent else rnd.randint(7000, 11000), rnd.randint(220, 420))
                if rnd.random() < (0.08 if recent else 0.04):
                    s.duration(400)
                    raise Failure("Rate limit (429) from model provider")
                s.duration(rnd.randint(2400, 5200)).output(f"Hi {who.title()}, thanks for reaching out…")
        except Failure:
            return
        to = f"{who}@gmail.com"
        run.check("send_email", to=to)          # external email -> flagged, but allowed
        with run.step("action", "send_email", to=to) as s:
            s.duration(rnd.randint(200, 500)).output("Sent")


def sales(lens, rnd, when, recent):
    co = rnd.choice(COMPANIES)
    with lens.run(input=f"Research {co}", started_at=when) as run:
        with run.step("tool", "search_web") as s:
            s.duration(rnd.randint(900, 2400)).output("9 results")
        loops = 4 if rnd.random() < 0.05 else 0
        for i in range(1 + loops):
            with run.step("llm", "summarize_company" + (f" (retry {i})" if i else ""), model="gpt-4o") as s:
                s.tokens(rnd.randint(14000, 24000) if not i else rnd.randint(22000, 30000), rnd.randint(350, 600)).duration(rnd.randint(3500, 7000))
        with run.step("llm", "score_lead", model="gpt-4o-mini") as s:
            s.tokens(rnd.randint(3000, 5000), rnd.randint(60, 120)).duration(rnd.randint(800, 1600)).output(f"fit_score: {rnd.randint(38, 94)}")
        try:
            with run.step("action", "crm_update") as s:
                if rnd.random() < 0.07:
                    s.duration(400)
                    raise Failure('Schema mismatch: field "fit_score" expects integer')
                s.duration(rnd.randint(300, 700)).output("Lead updated")
        except Failure:
            return


def hr(lens, rnd, when, recent):
    with lens.run(input="New hire onboarding", started_at=when) as run:
        with run.step("retrieval", "read_offer_letter") as s:
            s.duration(rnd.randint(300, 700))
        with run.step("action", "create_accounts", pii=True) as s:
            s.duration(rnd.randint(800, 1800)).output("email, Slack, HR portal created")
        try:
            with run.step("tool", "schedule_meetings") as s:
                if rnd.random() < 0.06:
                    s.duration(5000)
                    raise Failure("Timeout after 5000 ms: calendar_api")
                s.duration(rnd.randint(500, 1200)).output("4 meetings booked")
        except Failure:
            return
        with run.step("action", "send_welcome_email", to="new.hire@gmail.com") as s:
            s.duration(rnd.randint(200, 400)).output("Sent")


AGENTS = {"invoice-processor": (invoice, 0.34), "support-agent": (support, 0.44),
          "sales-research": (sales, 0.17), "hr-onboarding": (hr, 0.05)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--runs-per-day", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    lenses = {name: Cosignal(agent=name, api_url=a.url) for name in AGENTS}
    now, total = time.time() * 1000, 0
    for d in range(a.days - 1, -1, -1):
        for name, (fn, share) in AGENTS.items():
            for _ in range(max(1, round(a.runs_per_day * share))):
                when = now - d * 86_400_000 - rnd.randint(0, 86_399_000)
                fn(lenses[name], rnd, when, recent=(d == 0))
                total += 1
    decided = review_inbox(a.url, rnd, now)
    print(f"Sent {total} runs to {a.url} ({decided} older approval requests reviewed). Open {a.url} to see the dashboard.")


def review_inbox(url, rnd, now):
    """Approve or reject held actions older than a day, the way a finance team works through its inbox.
    Today's requests stay pending so the demo has something to approve."""
    import json, urllib.request
    pending = json.loads(urllib.request.urlopen(f"{url}/v1/approvals?status=pending").read())
    n = 0
    for ap in pending:
        if ap["created_at"] > now - 86_400_000:
            continue
        ok = rnd.random() < 0.85
        body = {"decision": "approve" if ok else "reject", "by": rnd.choice(["maria.lopez", "dev.patel", "sam.chen"]),
                "note": "Matches PO and contract" if ok else "Duplicate invoice, already paid"}
        req = urllib.request.Request(f"{url}/v1/approvals/{ap['id']}/decision", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req).read()
        n += 1
    return n


if __name__ == "__main__":
    main()
