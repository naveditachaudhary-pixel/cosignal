# Cosignal Launch & Discoverability Playbook

This document contains actionable templates, scripts, and multi-channel launch strategies to drive visibility, stars, and adoption for **Cosignal**.

---

## 1. Quick GitHub Metadata Setup

Run the included automated helper script or configure manually via the GitHub UI:

```bash
./scripts/update_github_settings.sh
```

### Manual Configuration (GitHub Repo → About ⚙️):
- **Description**: `Open-source human-in-the-loop approval, policy enforcement, and audit trails for AI agents that execute payments and financial actions.`
- **Website**: `https://naveditachaudhary-pixel.github.io/cosignal/`
- **Topics**: `ai-agents`, `ai-governance`, `human-in-the-loop`, `fintech`, `agent-observability`, `approval-workflow`, `audit-trail`, `fastapi`, `python`, `payments`

---

## 2. Core Positioning & Narrative

> ⚠️ **The Core Problem**: *What happens when an autonomous AI agent attempts to disburse a $15,000 payment without human approval?*
> 
> **The Solution**: Cosignal introduces institutional "Maker-Checker" dual control to AI agent frameworks. Before any money moves, rules check the threshold. If high risk, execution pauses synchronously, notifies human approvers in Slack/Inbox, and resumes only after explicit approval—leaving an immutable audit trail.

---

## 3. Hacker News Launch (Show HN)

**Suggested Title**: `Show HN: Cosignal – Human approval and audit trails for AI agents moving money`

**Post Body**:
```markdown
Hi HN! I built Cosignal (https://github.com/naveditachaudhary-pixel/cosignal) because more developers are giving AI agents access to real money—paying invoices, processing refunds, and executing transfers.

The standard pattern today is letting LLM tools execute actions immediately, or relying on custom post-facto logging. In banking and finance, any action moving real money requires a "maker-checker" / dual-control principle: one system initiates, a human policy reviewer approves.

Cosignal sits between your Python AI agent and external execution tools:
1. Guard: When your agent calls `cosignal.check("create_payment", amount=15000)`, Cosignal evaluates policies defined in YAML.
2. Pause & Approve: If an action exceeds limits (e.g., > $10,000 or new vendor), the agent execution lock waits while an alert hits Slack and the Cosignal Approvals Inbox.
3. Resume: The instant a human reviewer clicks "Approve", the agent continues execution cleanly.
4. Record & Audit: Every LLM token, tool call, policy decision, and human intervention is logged to an append-only audit trail.

The SDK is zero-dependency Python and never crashes your agent if the server is down (fails open or closed based on config).

Live Demo (no sign-up): https://naveditachaudhary-pixel.github.io/cosignal/
GitHub Repo: https://github.com/naveditachaudhary-pixel/cosignal

I'd love feedback on how you're handling risk and human intervention for agentic workflows!
```

---

## 4. Reddit Strategy & Post Drafts

### Subreddit 1: r/LocalLLaMA & r/ArtificialIntelligence
**Title**: `What happens when an AI agent tries to transfer $15,000? We built an open-source human-in-the-loop guardrail system (Cosignal)`

**Post Content**:
```markdown
As autonomous AI agents shift from chatting to performing real-world transactions (invoice processing, customer refunds, wire transfers), failure modes become financial risks.

Generic APM/tracing tools give you dashboards *after* an agent spends money. We wanted a lightweight, institutional-grade dual-control guardrail system.

We built **Cosignal** (MIT open source):
- 🛑 **Synchronous Hold**: Holds high-risk agent tool calls in place.
- 💬 **Slack / Inbox Approval**: Financial admins get instant Approve/Reject triggers.
- 📜 **Append-only Audit Trail**: Complete cryptographic log of model inputs, tool outputs, and human decisions.
- ⚙️ **YAML Policies**: Configure rules like high-value payment thresholds, vendor verification, or PII access outside application code.

SDK usage is a simple Python context manager:
```python
decision = lens.check("create_payment", amount=15000, vendor="Acme")
if decision.allowed:
    pay(invoice)
else:
    notify_team(decision.reason)
```

GitHub: https://github.com/naveditachaudhary-pixel/cosignal
Live Interactive Demo: https://naveditachaudhary-pixel.github.io/cosignal/

What rules or safety limits are you setting on your autonomous tool calls today?
```

### Subreddit 2: r/Python
**Title**: `Cosignal – Open-source Python SDK for human approval & audit trails on autonomous AI actions`

---

## 5. X / Twitter Thread Draft

**Tweet 1 (The Hook)**:
What happens when an AI agent is allowed to move $15,000 without human approval? 💸🤖

Most AI observability tools tell you what happened *after* money left your bank account.

We built Cosignal: Open-source human-in-the-loop approval & audit trails for financial AI agents. 👇

**Tweet 2 (The Solution)**:
Banks use "maker-checker" controls: one person prepares a wire, another signs off. 

Cosignal applies this exact institutional principle to AI agents:
1. Agent checks policy
2. High-value action pauses
3. Admin approves in Slack / Web Inbox
4. Agent resumes execution

**Tweet 3 (Visual Demo)**:
Here's a 15-second visual breakdown:
[Attach docs/demo.gif]

Rules live in clean YAML (`policies.yaml`), not hardcoded in Python logic. Change thresholds without redeploying.

**Tweet 4 (Developer Experience)**:
Zero-dependency Python SDK. Non-blocking & crash-resilient buffer.

```python
with run.check("create_payment", amount=invoice["amount"]) as decision:
    if decision.allowed:
        pay(invoice)
```

**Tweet 5 (Links & CTA)**:
Try the zero-setup live demo or star the repo on GitHub:

▶️ Live Demo: https://naveditachaudhary-pixel.github.io/cosignal/
⭐ GitHub: https://github.com/naveditachaudhary-pixel/cosignal

#AIAgents #Python #OpenSource #Fintech #AI governance

---

## 6. LinkedIn Post Draft

**Post Copy**:
```text
Giving AI agents access to corporate bank accounts and ERP systems is exciting—until an unmonitored model attempts an unauthorized $15,000 disbursement.

In traditional finance, institutional governance relies on the "Maker-Checker" principle (dual control). Why should autonomous AI agents be any different?

Today we're open-sourcing Cosignal: Human-in-the-loop approval, policy enforcement, and auditability built specifically for AI agents that move money.

Key capabilities:
• Policy Enforcement: Intercept high-value transfers, new vendor payees, or PII access.
• Human Intervention: Pause agent execution until a team member approves via Slack or web inbox.
• Immutable Audit Log: Flight-recorder style replay for compliance and financial auditors.

Try out the live demo (no registration required):
https://naveditachaudhary-pixel.github.io/cosignal/

Check out the code on GitHub:
https://github.com/naveditachaudhary-pixel/cosignal

#Fintech #AIGovernance #AIAgents #Python #OpenSource
```

---

## 7. Relevant Discord Communities to Share

1. **LangChain / LangGraph Discord**: `#share-your-project`
2. **OpenAI Developer Community**: `#show-and-tell`
3. **CrewAI & AutoGen Discords**: `#projects-showcase`
