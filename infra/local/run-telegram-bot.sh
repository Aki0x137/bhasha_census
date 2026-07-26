#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate 2>/dev/null || true

if [ -f .env ]; then
  set -o allexport; source .env; set +o allexport
fi

# Telegram allows only ONE getUpdates poller per bot token.
existing="$(pgrep -f 'python -m apps.telegram.bot' || true)"
if [ -n "$existing" ]; then
  echo "[bhasaha] Another bot is already running (pid: $existing)."
  echo "[bhasaha] Stopping it first to avoid Conflict errors..."
  pkill -f 'python -m apps.telegram.bot' || true
  sleep 2
fi

echo "[bhasaha] Starting Telegram bot..."
python -m apps.telegram.bot
