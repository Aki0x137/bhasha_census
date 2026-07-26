# bhasaha_census

Local-first MVP for KYC/census automation via Telegram and AI agents (Linux / macOS).

- **Architecture & MVP design**: [`docs/liveliness_check_mvp.md`](docs/liveliness_check_mvp.md)
- **Project constitution** (scope, stack, contracts, decision authority): [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- **Feature spec**: [`specs/001-telegram-kyc-census/spec.md`](specs/001-telegram-kyc-census/spec.md)
- **Quickstart**: [`specs/001-telegram-kyc-census/quickstart.md`](specs/001-telegram-kyc-census/quickstart.md)

**Stack**: Python 3.11+, pip, Temporal, LangGraph, FastAPI, Pydantic v2, Sarvam (STT + document digitization), AWS Bedrock (Nova Lite verdict explainer), OpenCV/MediaPipe (local video plugins), SQLite + filesystem evidence.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-video.txt      # OpenCV + MediaPipe for video worker
cp .env.example .env                       # fill in secrets
```

Run all three processes in separate terminals:

```bash
bash infra/local/run-api.sh
bash infra/local/run-video-worker.sh
bash infra/local/run-telegram-bot.sh
```

## Smoke test (no Telegram needed)

```bash
# 1. List registered plugins
curl http://localhost:8000/video/plugins | python3 -m json.tool

# 2. Run pipeline with demo fixture (replace path with real image)
curl -X POST http://localhost:8000/video/verify \
  -H "Content-Type: application/json" \
  -d @evidence/demo/job.json.example | python3 -m json.tool
```

## Run unit tests

```bash
pytest -q
```

## Layout

```
apps/
  api/              FastAPI app, session DB, video routes
  telegram/         Bot, handlers, i18n (EN + HI)
services/
  video/            Pluggable pipeline, 9 default plugins, Temporal activity
  speech/           Sarvam STT adapter + phrase verifier
  document/         Sarvam doc digitizer + field matcher
  orchestrator/     EvidenceBundle builder, Bedrock explainer, finalize
  policy/           Deterministic verdict fusion + challenge plan generator
shared/
  schemas/          All Pydantic typed contracts
  utils/            Logging, evidence paths, cleanup
infra/local/        Run scripts, README
tests/              pytest unit + integration
evidence/           Session media (gitignored, demo fixtures only)
```

## Privacy notes

- All captured media stored only under `evidence/<session_id>/`
- `evidence/` is gitignored — never committed
- Sessions expire after 24 hours; use `expire_abandoned_sessions()` in session_store
- Raw media cleanup: `shared/utils/evidence_cleanup.py`
