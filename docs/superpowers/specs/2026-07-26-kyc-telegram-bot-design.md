# KYC Bot — MVP Design Spec

**Date:** 2026-07-26
**Status:** Approved for planning
**Author:** Pratik Sabata

## 1. Goal

Build an MVP that performs **identity proofing** (KYC) through a chat interface. A user proves their identity by submitting a government ID and passing a live selfie challenge; the system extracts ID data, confirms the selfie is a live person, and matches that person's face to the ID.

Hard constraints:

- **No infrastructure cost and no billing.** Everything runs on a single machine.
- **All open source.** No proprietary hosted APIs in the default path.

## 2. Scope

### In scope

- ID document OCR (extract name / DOB / ID number / expiry).
- Active liveness challenge (blink / head-turn) via a short video.
- Face match between the live selfie and the ID photo.
- Automatic pass/fail decisioning with a manual-review queue for borderline cases.
- Consent capture and an append-only audit trail.
- Encrypted at-rest storage of images, video, and extracted PII.
- A minimal admin UI to resolve the review queue.

### Out of scope (explicitly)

- Sanctions / PEP / watchlist screening.
- Regulatory certification or legal compliance sign-off.
- HSM / KMS key management (single env key for MVP).
- Multi-tenancy, horizontal scale, production hardening.
- Passive (texture-based) anti-spoof liveness — active challenge only for MVP.

This is an identity-proofing MVP, **not** a compliance-certified product.

## 3. Channel strategy

- **Telegram-first.** Telegram's Bot API is free, official, has no ban risk, and handles files/video well. Chosen over WhatsApp for the MVP to satisfy the zero-cost / zero-risk constraint.
- **Channel-agnostic core.** All chat interaction goes through a `MessagingChannel` interface. Telegram is one implementation. A WhatsApp adapter (Meta Cloud API) can be added later as a drop-in implementation with no changes to the KYC flow.

## 4. Verification / ML strategy

- **Self-hosted open-source models**, each behind a pluggable `VerificationProvider` interface so a different (even cloud) implementation could be swapped in without touching the flow.
- Default implementations:
  - **OCR:** PaddleOCR.
  - **Face match:** InsightFace (embedding cosine similarity).
  - **Liveness:** MediaPipe face-landmarks (eye-aspect-ratio for blink, yaw for head-turn).

## 5. Architecture

Single Python process, run with `python -m kyc_bot`. Internally modular for isolation, swappability, and testability.

```
kyc_bot/
  channels/
    base.py          # MessagingChannel interface
    telegram.py      # Telegram implementation (long-polling)
  flow/
    state_machine.py # KYC conversation states + transitions
    session.py       # per-user session state (persisted)
  verification/
    base.py          # VerificationProvider interface
    ocr.py           # PaddleOCR provider
    face.py          # InsightFace provider
    liveness.py      # MediaPipe provider
    orchestrator.py  # runs the 3 steps, scores, returns a Decision
  storage/
    db.py            # SQLite (records, sessions, audit, review queue)
    vault.py         # encrypted file storage for images/video
  admin/
    app.py           # FastAPI review-queue UI + approve/reject
  config.py          # thresholds, paths, keys (env-driven)
  __main__.py        # wiring; starts bot + admin
```

### Key interfaces (the swap points)

- **`MessagingChannel`** — everything the flow needs from a chat platform (send text, send prompt/buttons, fetch an uploaded file/photo/video, identify the user). Telegram now; WhatsApp later.
- **`VerificationProvider`** — common shape `process(input) -> result + score`. Each of OCR / face / liveness is a provider. OSS impls are defaults; alternatives drop in.

### Concurrency

The bot loop is async. Each CPU-heavy verification call runs via `run_in_executor` on a thread pool so ML never blocks message handling. No external queue/broker — stays single-process, zero-infra.

## 6. Conversation flow (state machine)

Session state is persisted to SQLite after every transition, so a user can resume across a bot restart.

```
START
  → /start → greet, explain steps + consent ask
CONSENT            → agree → next ; decline → END(declined)
COLLECT_ID_FRONT   → "Send a photo of your ID (front)" → get image
COLLECT_ID_BACK    → (optional, configurable)
LIVENESS_CHALLENGE → random challenge (blink / turn head)
                     → user sends a short video
COLLECT_SELFIE     → best frontal frame extracted from the video
PROCESSING         → "Verifying…" (async job)
DECISION           → PASS | FAIL | PENDING_REVIEW
  PASS    → "✅ Verified"
  FAIL    → "❌ Couldn't verify" + retry (capped)
  PENDING → "⏳ Under review, we'll message you"
END
```

Notes:

- **Consent is state #1** and logged to the audit table before any capture.
- **Liveness + selfie share one capture:** the challenge video proves liveness (MediaPipe confirms the motion), and its sharpest frontal frame becomes the selfie for face-match.
- **Retry cap** (default 3) per stage; exceeding it routes to `PENDING_REVIEW`, not a hard fail.
- **Resumable:** the session row stores the current state and references to collected artifacts.

## 7. Verification pipeline & decisioning

At `PROCESSING`, the orchestrator runs three providers (in the thread pool) and combines scores into one `Decision`.

1. **OCR (PaddleOCR):** extract text from the ID, parse name / DOB / ID number / expiry via heuristics + regex. Output fields + `ocr_quality` (low on blur / glare / no fields).
2. **Liveness (MediaPipe):** track landmarks across video frames, confirm the requested motion (EAR drop = blink; yaw change = head turn). Output `liveness_passed` + confidence; select the sharpest frontal frame as the selfie.
3. **Face match (InsightFace):** embeddings for selfie vs. face cropped from the ID; output cosine `face_sim` in [0, 1].

Decision logic (thresholds in `config.py`, env-tunable):

```
if not liveness_passed         → FAIL (spoof suspected)
elif ocr_quality < Q_MIN       → FAIL (unreadable doc) [retry-eligible]
elif face_sim >= PASS_HI and ocr_quality >= Q_OK  → PASS
elif face_sim <  FAIL_LO       → FAIL
else                           → PENDING_REVIEW      # borderline middle band
```

The **PENDING band** is: liveness OK, doc readable, but `face_sim` in the ambiguous `[FAIL_LO, PASS_HI)` range → a human decides.

Every run writes an **audit record**: provider scores, thresholds used, decision, timestamp, session id.

### Manual review (FastAPI admin)

A minimal list of `PENDING_REVIEW` cases showing the ID crop, selfie, extracted fields, and the three scores, with **Approve / Reject** buttons. On action: update the record, write an audit row, and push the outcome to the user through the same `MessagingChannel` (review UI stays channel-agnostic). Bound to localhost by default.

## 8. Storage schema (SQLite via SQLModel/SQLAlchemy)

```
sessions     (id, channel, channel_user_id, state, created_at, updated_at)
kyc_records  (id, session_id, status, ocr_fields_json[enc], face_sim,
              liveness_conf, ocr_quality, decided_at, decided_by)
artifacts    (id, record_id, kind[id_front|id_back|selfie|video],
              vault_path, sha256, created_at)
audit_log    (id, session_id, event, detail_json, actor, ts)   # append-only
review_queue (record_id, enqueued_at, resolved_at, resolver)
```

## 9. Security & privacy (MVP-appropriate)

- **Encryption at rest.** Images/video in the vault encrypted with Fernet (AES-128-CBC + HMAC). Extracted PII fields encrypted before hitting the DB.
- **Key handling.** Single `KYC_MASTER_KEY` from env / key file, never committed. Documented as the thing to move to a KMS later.
- **Consent + audit.** Consent event and every decision are append-only in `audit_log`.
- **Retention.** Config'd TTL (e.g. purge raw video after decision; keep record + audit). Ships as a purge command; cron later.
- **Least exposure.** Admin UI on localhost; no PII in logs (ids + scores only).

## 10. Testing strategy

- **Unit:** state-machine transitions (table-driven); decision logic across every threshold band; OCR field parsing on sample strings; vault encrypt/decrypt round-trip.
- **Provider contract tests:** each provider against fixed sample images/videos with expected score ranges; fakes implement the interfaces so flow tests need no real ML.
- **Flow integration:** a `FakeChannel` drives a full scripted journey (consent → docs → liveness → decision) with fake providers, asserting DB + audit state. This is the backbone test.
- **Admin:** approve/reject updates the record and notifies the user via `FakeChannel`.

## 11. Tech stack

- Python 3.11+
- `python-telegram-bot` (async, long-polling)
- PaddleOCR, InsightFace, MediaPipe, OpenCV
- SQLModel/SQLAlchemy + SQLite
- FastAPI + Uvicorn (admin)
- `cryptography` (Fernet)
- pytest

## 12. Future extensions (not built now)

- WhatsApp adapter (Meta Cloud API).
- Passive anti-spoof liveness (MiniFASNet / Silent-Face).
- Sanctions/PEP screening; KMS-backed keys; Postgres + MinIO; multi-tenant.
