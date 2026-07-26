#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

source .venv/bin/activate 2>/dev/null || true

if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

echo "[bhasaha] Starting API on http://localhost:8000"
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
