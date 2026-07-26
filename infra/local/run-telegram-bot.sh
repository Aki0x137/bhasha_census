#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate 2>/dev/null || true

if [ -f .env ]; then
  set -o allexport; source .env; set +o allexport
fi

echo "[bhasaha] Starting Telegram bot..."
python -m apps.telegram.bot
