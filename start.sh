#!/usr/bin/env bash
# One-command start: builds the dashboard (first run only) and serves everything on http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r backend/requirements.txt
  .venv/bin/python -m playwright install chromium
fi
if [ ! -d frontend/dist ]; then
  (cd frontend && npm install && npm run build)
fi

cd backend
exec ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
