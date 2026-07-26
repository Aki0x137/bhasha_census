# Agent Brief — Track C: Backend + Sarvam + Policy/Verdict

> Paste the block below into the backend teammate's AI agent. Self-contained.
> Full context: [`docs/PRD.md`](../PRD.md). This track is the natural owner of the
> shared step: create `shared/schemas/` from PRD §5 first, commit + push so the
> other two tracks can pull.

```text
You are building the backend, Sarvam integration, and decision engine for "Praman",
a local liveness / anti-deepfake verification MVP. Repo: bhasaha_census
(FastAPI + Uvicorn, SQLite via SQLModel, Pydantic v2). FIRST read docs/PRD.md fully,
especially §5 (contracts), §6 (REST API), §7 (your track), §8 (policy).

Your deliverable (owns apps/api/, services/speech/, services/document/,
services/policy/, storage/):
- FastAPI app implementing exactly the REST contract in PRD §6 (/sessions, /consent,
  /event, GET /sessions/{id}, /finalize). Session + deterministic challenge engine
  (random under a test seed). Monotonic state machine (PRD §4.2).
- Speech provider: SpeechProvider interface + SarvamSpeechProvider calling
  POST https://api.sarvam.ai/speech-to-text (Saaras v3, REST, header
  api-subscription-key, model="saaras:v3", mode="transcribe") -> SpeechScores with a
  phrase_match_score vs the expected random phrase. Plus FakeSpeechProvider.
- Document provider: DocProvider interface + SarvamDocProvider calling
  POST https://api.sarvam.ai/doc-digitization/job/v1 (poll job_id, output_format=json)
  -> DocScores with detected_fields; MASK any ID number to last-4 before storing/
  returning; never log the full number. Plus FakeDocProvider. (Fallback OCR: PaddleOCR
  local, optional.)
- Deterministic policy engine (PRD §8): fuse VideoScores+SpeechScores+DocScores
  (+optional FaceScores) into VerdictResult (PASS/REVIEW/FAIL/NEEDS_MORE_EVIDENCE) with
  reason_codes. LLM must NOT be in the decision path. Weights/thresholds env-tunable.
- Storage: SQLite (sessions, records, artifacts, append-only audit_log). Encrypt PII
  fields + artifacts at rest with Fernet (key from env KYC_MASTER_KEY, never committed).
  Every verdict writes an audit row. Log consent as the first audit event.
- Config flag (env SARVAM_KEY present) selects real Sarvam vs Fake providers with no
  code change. Ship a fake-mode default so the whole app runs offline.

Contract: import all types from shared/schemas/; do NOT change them without announcing
to the team. Call services/video via its plain Python interface (import the
FakeVideoProvider until Pratik's is ready).

Golden acceptance test: post a scripted fixture event stream -> a deterministic
VerdictResult; unit tests cover every policy threshold band (PASS/REVIEW/FAIL/hard-fail)
and the ID-masking + Fernet round-trip.

Guardrails: no real UIDAI/government/KYC backend or watchlist; consent required before
capture; IDs masked; sample data only. Do NOT add Temporal, LangGraph, Bedrock, or a
Telegram bot.
```
