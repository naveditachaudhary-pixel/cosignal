#!/usr/bin/env bash
# Update GitHub repository Topics, Description, and Website URL via API or GitHub CLI

REPO="naveditachaudhary-pixel/cosignal"
DESC="Open-source human-in-the-loop approval, policy enforcement, and audit trails for AI agents that execute payments and financial actions."
WEBSITE="https://naveditachaudhary-pixel.github.io/cosignal/"
TOPICS='["ai-agents","ai-governance","human-in-the-loop","fintech","agent-observability","approval-workflow","audit-trail","fastapi","python","payments"]'

echo "=========================================================="
echo " 🛠️  Cosignal GitHub Metadata Configurator"
echo "=========================================================="

if command -v gh &>/dev/null; then
  echo "Using GitHub CLI (gh)..."
  gh repo edit "$REPO" \
    --description "$DESC" \
    --homepage "$WEBSITE" \
    --add-topic ai-agents,ai-governance,human-in-the-loop,fintech,agent-observability,approval-workflow,audit-trail,fastapi,python,payments
  echo "✅ GitHub settings updated via gh CLI!"
elif [ -n "$GITHUB_TOKEN" ]; then
  echo "Using GitHub REST API with GITHUB_TOKEN..."
  curl -s -X PATCH -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$REPO" \
    -d "{\"description\":\"$DESC\",\"homepage\":\"$WEBSITE\"}" > /dev/null
    
  curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$REPO/topics" \
    -d "{\"names\":$TOPICS}" > /dev/null
  echo "✅ GitHub settings updated via REST API!"
else
  echo "ℹ️  Neither 'gh' CLI nor GITHUB_TOKEN environment variable was detected."
  echo "To update manually via web browser:"
  echo " 1. Go to https://github.com/naveditachaudhary-pixel/cosignal"
  echo " 2. Click the ⚙️ gear icon next to 'About' on the right sidebar."
  echo " 3. Description: $DESC"
  echo " 4. Website: $WEBSITE"
  echo " 5. Topics: ai-agents, ai-governance, human-in-the-loop, fintech, agent-observability, approval-workflow, audit-trail, fastapi, python, payments"
fi
