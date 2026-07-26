# Local Developer Setup (Linux / macOS)

## Prerequisites

- Python 3.11+
- pip
- (Optional) [Temporal CLI](https://docs.temporal.io/cli) for durable workflows

## Quick start

```bash
cd /path/to/bhasaha_census

# Create and activate virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install full dependencies
pip install -r requirements.txt

# Install video worker dependencies (OpenCV, MediaPipe)
pip install -r requirements-video.txt
```

## Local run order

Start each process in a separate terminal:

```bash
# 1. API
bash infra/local/run-api.sh

# 2. Video Temporal worker
bash infra/local/run-video-worker.sh

# 3. Telegram bot
bash infra/local/run-telegram-bot.sh
```

## Environment variables

Copy `.env.example` to `.env` and fill in:

```
TELEGRAM_BOT_TOKEN=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-south-1
SARVAM_API_KEY=...
TEMPORAL_HOST=localhost:7233
```

## Acceptance smoke test

See `specs/001-telegram-kyc-census/quickstart.md` for step-by-step curl + bot demo.
