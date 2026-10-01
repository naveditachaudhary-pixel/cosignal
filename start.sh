#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=================================================="
echo "  🚀 Cosignal: AI Agent Guardrails & Audit Trail"
echo "=================================================="

# Check for Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Error: Python 3 is required. Please install Python 3."
    exit 1
fi

# Set up virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
    echo "⬇️  Installing dependencies from requirements.txt..."
    .venv/bin/pip install -q -r requirements.txt
fi

# Ensure port 8000 is free or notify
if lsof -i :8000 &>/dev/null; then
    echo "⚠️  Port 8000 is already in use. You might already have Cosignal running."
fi

# Open browser automatically after server starts
(
    sleep 1.5
    if command -v open &>/dev/null; then
        open http://localhost:8000
    elif command -v xdg-open &>/dev/null; then
        xdg-open http://localhost:8000
    fi
) 2>/dev/null &

echo "✨ Cosignal Dashboard: http://localhost:8000"
echo "🛑 Press Ctrl+C to stop the server."
echo "=================================================="

exec .venv/bin/uvicorn server.app:app --port 8000
