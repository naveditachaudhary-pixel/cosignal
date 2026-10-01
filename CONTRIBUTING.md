# Contributing

Thanks for helping! Issues and pull requests are welcome.

## Run it locally
```bash
pip install -r requirements.txt
uvicorn server.app:app --port 8000      # API + dashboard at http://localhost:8000
python -m examples.simulate_agents      # sample agent traffic
pytest -q                               # tests
```

## Good first contributions
- New guardrail examples in `policies.yaml` (e.g. duplicate-invoice detection, daily spend caps)
- Integrations: LangChain / LangGraph callback, OpenAI Agents SDK tracing processor, CrewAI
- Notification channels: Microsoft Teams, email
- Dashboard improvements (accessibility, filters, exports)

## Guidelines
- Keep the SDK dependency-free (standard library only).
- Add or update a test for any behaviour change.
- Never commit real customer, payment or personal data. Use the simulator.
