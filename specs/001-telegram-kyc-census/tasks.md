---
description: "Task list for Telegram KYC/census MVP with pluggable video layer"
---

# Tasks: Telegram KYC & Census Automation MVP

**Input**: Design documents from `/specs/001-telegram-kyc-census/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Optional — not explicitly requested in the feature specification; omit dedicated TDD tasks. Validate via quickstart smoke checks in Polish.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: User story label (US1–US4) for story-phase tasks only
- Paths assume repo root layout from plan.md

## Path Conventions

- **MVP**: `apps/telegram/`, `apps/api/`, `services/{video,speech,document,orchestrator,policy}/`, `shared/schemas/`, `infra/local/`, `tests/`, `evidence/`

**Terminology**: Spec “enrollment decision” ≡ plan/tasks “enrollment verdict”
(`approved` | `needs_review` | `rejected` | `needs_more_evidence`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton and dependency baseline for Linux/macOS

- [X] T001 Create MVP directory tree `apps/api/`, `apps/telegram/`, `services/video/plugins/`, `services/speech/`, `services/document/`, `services/orchestrator/`, `services/policy/`, `shared/schemas/`, `shared/utils/`, `infra/local/`, `evidence/`, `tests/unit/video/` per `specs/001-telegram-kyc-census/plan.md`
- [X] T002 [P] Add root `requirements.txt` with pydantic, fastapi, uvicorn, temporalio, python-telegram-bot (or chosen Telegram SDK), and `requirements-video.txt` with opencv-python-headless, mediapipe, numpy per `specs/001-telegram-kyc-census/research.md`
- [X] T003 [P] Add `evidence/.gitignore` and root `.gitignore` entries for `.venv/`, `__pycache__/`, `evidence/**` (keep `evidence/.gitkeep`) in repository root
- [X] T004 [P] Add `infra/local/README.md` documenting venv + pip install on Linux/macOS referencing `specs/001-telegram-kyc-census/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Typed contracts, session store, video plugin skeleton, API shell — MUST complete before user stories

**⚠️ CRITICAL**: No user story work begins until this phase is complete

- [X] T005 Create shared enums and reason-code constants in `shared/schemas/common.py`
- [X] T006 [P] Implement Pydantic `MediaRef`, `ChallengeParams`, `VerificationTarget`, `VerificationJob` in `shared/schemas/verification_job.py` per `specs/001-telegram-kyc-census/contracts/verification-job.md` (depends on T005)
- [X] T007 [P] Implement Pydantic `PluginResult`, `VideoEvidenceScores`, `TargetEvaluation`, `VideoEvidence` in `shared/schemas/video_evidence.py` per `specs/001-telegram-kyc-census/contracts/video-evidence.md` (depends on T005)
- [X] T008 [P] Implement `EnrollmentSession`, `CensusProfile`, and session status enums in `shared/schemas/session.py` per `specs/001-telegram-kyc-census/data-model.md` (depends on T005; `ChallengeParams` live in `verification_job.py`, not a separate `challenge.py`)
- [X] T009 Implement SQLite session repository (create/get/update, one active session per `user_ref`) in `apps/api/db/session_store.py`
- [X] T010 Implement evidence path helpers (`evidence/{session_id}/video/`) in `shared/utils/evidence_paths.py`
- [X] T011 Implement video plugin Protocol + in-process registry in `services/video/registry.py`
- [X] T012 Implement empty pipeline orchestrator stub `run_verification_job(job) -> VideoEvidence` in `services/video/pipeline.py` that validates job and returns placeholder scores
- [X] T013 Implement Temporal activity wrapper `analyze_verification_job` in `services/video/activity.py` calling `services/video/pipeline.py`
- [X] T014 Create FastAPI app skeleton with health check in `apps/api/main.py`
- [X] T015 Add `GET /video/plugins` listing registry entries in `apps/api/routes/video.py` and register router on app from T014 per `specs/001-telegram-kyc-census/contracts/video-api.md` (depends on T014)
- [X] T016 Wire `POST /video/verify` to pipeline in `apps/api/routes/video.py` with 422/404 mappings per `specs/001-telegram-kyc-census/contracts/video-api.md` (depends on T014, T015)
- [X] T017 Add structured logging helper for session/job/challenge events in `shared/utils/logging.py`
- [X] T018 Add `infra/local/run-api.sh` to start uvicorn on localhost for Linux/macOS

**Checkpoint**: Schemas validate; `/video/plugins` and `/video/verify` respond; session store works — user stories can proceed. Note: T006–T008 may run in parallel only after T005.

---

## Phase 3: User Story 1 - Start Enrollment and Capture Census Basics (Priority: P1) 🎯 MVP

**Goal**: Telegram bot starts session, collects consent, captures and confirms minimal census profile without media.

**Independent Test**: Start bot → accept consent → answer name, DOB/age, gender, locality, household size → confirm summary → session status ready for verification (no media required).

### Implementation for User Story 1

- [X] T019 [P] [US1] Implement challenge-plan stub generator (empty or deferred challenges) in `services/policy/challenge_plan.py`
- [X] T020 [P] [US1] Implement consent + census Q&A + challenge prompt message copy (en + one Indian language) in `apps/telegram/i18n/messages.py` (FR-005)
- [X] T021 [US1] Implement Telegram bot entrypoint and config loader in `apps/telegram/bot.py`
- [X] T022 [US1] Implement `/start` handler: create or resume single active session in `apps/telegram/handlers/start.py` using `apps/api/db/session_store.py`
- [X] T023 [US1] Implement consent accept/decline handlers that block media until accepted in `apps/telegram/handlers/consent.py` using `apps/telegram/i18n/messages.py`
- [X] T024 [US1] Implement census Q&A state machine (name, dob_or_age, gender, locality, household_size) in `apps/telegram/handlers/census.py` using localized prompts from `apps/telegram/i18n/messages.py` (FR-005)
- [X] T025 [US1] Persist `CensusProfile` and confirmation summary to session in `apps/telegram/handlers/census.py` via `apps/api/db/session_store.py`
- [X] T026 [US1] Mark session ready-for-verification after profile confirm in `apps/telegram/handlers/census.py`
- [X] T027 [US1] Add conversation guide in `services/orchestrator/census_guide.py` used by `apps/telegram/handlers/census.py`: deterministic/scripted stub is OK for US1 demo if it only restates user-provided answers and never invents personal facts (FR-004 partial); full LangGraph/Bedrock guidance may land with US4 explainer patterns
- [X] T028 [US1] Add `infra/local/run-telegram-bot.sh` to run the bot locally

**Checkpoint**: US1 independently demoable on Telegram without video/speech/document

---

## Phase 4: User Story 2 - Prove Presence with Live Challenges (Priority: P2)

**Goal**: Randomized presence challenges over Telegram; pluggable video layer scores media with params/targets; speech phrase challenge recorded.

**Independent Test**: From ready session, complete one physical challenge (photo/video) and one speech challenge; each yields stored evidence with reason codes.

### Implementation for User Story 2

- [X] T029 [P] [US2] Implement `face_detector` plugin in `services/video/plugins/face_detector.py`
- [X] T030 [P] [US2] Implement `frame_quality` plugin in `services/video/plugins/frame_quality.py`
- [X] T031 [P] [US2] Implement `pose_estimator` plugin in `services/video/plugins/pose_estimator.py`
- [X] T032 [P] [US2] Implement `face_tracker` plugin in `services/video/plugins/face_tracker.py`
- [X] T033 [P] [US2] Implement `blink_detector` plugin in `services/video/plugins/blink_detector.py`
- [X] T034 [P] [US2] Implement `mouth_movement_detector` plugin in `services/video/plugins/mouth_movement_detector.py`
- [X] T035 [P] [US2] Implement `spoof_detector` heuristic plugin in `services/video/plugins/spoof_detector.py`
- [X] T036 [P] [US2] Implement `temporal_anomaly_detector` plugin in `services/video/plugins/temporal_anomaly_detector.py`
- [X] T037 [US2] Register default MVP plugin profile and wire plugins into `services/video/registry.py`
- [X] T038 [US2] Implement scoring aggregation + `hard_fail_hint` + reason codes (incl. `MULTI_FACE`) + `targets_evaluation` (defer `document_field`) in `services/video/scoring.py`
- [X] T039 [US2] Complete `services/video/pipeline.py` to load media, run enabled plugins, call scoring, write optional debug `payload_ref` under `evidence/`
- [X] T040 [US2] Add CLI entry `python -m services.video.pipeline` in `services/video/__main__.py` per quickstart
- [X] T041 [P] [US2] Implement challenge engine issuing `LOOK_LEFT_RIGHT` / `BLINK_TWICE` / `SMILE_AND_TILT` with seed in `services/policy/challenge_engine.py`; prompt strings resolved via `apps/telegram/i18n/messages.py` (FR-005)
- [X] T042 [US2] Build `VerificationJob` from challenge + census claim targets in `apps/telegram/services/job_builder.py`
- [X] T043 [US2] Implement Telegram presence challenge handlers (prompt, download media to `evidence/`, call verify) in `apps/telegram/handlers/presence_challenge.py`; on `MULTI_FACE` / `hard_fail_hint` send clear user-visible retry or fail message (not silent)
- [X] T044 [US2] Implement retry/timeout/exhausted-attempt and multi-face messaging in `apps/telegram/handlers/presence_challenge.py`
- [X] T045 [P] [US2] Implement typed `SpeechEvidence` Pydantic schema in `shared/schemas/speech_evidence.py` per `specs/001-telegram-kyc-census/data-model.md` (constitution Principle III)
- [X] T046 [P] [US2] Implement Sarvam STT client adapter (with fake/offline mode) in `services/speech/sarvam_stt.py`
- [X] T047 [US2] Implement speech phrase match + latency scoring returning `SpeechEvidence` in `services/speech/phrase_verifier.py` (depends on T045)
- [X] T048 [US2] Implement Telegram voice challenge handler storing typed speech evidence on session in `apps/telegram/handlers/speech_challenge.py` using `apps/telegram/i18n/messages.py` for prompts
- [X] T049 [US2] Add Temporal worker entrypoint loading video activity in `services/video/worker.py` and `infra/local/run-video-worker.sh`

**Checkpoint**: US2 works with US1 session; `/video/verify` and bot challenges produce `VideoEvidence` and `SpeechEvidence`

---

## Phase 5: User Story 3 - Capture ID Document and Cross-Check Claims (Priority: P3)

**Goal**: Capture ID image, extract fields via document service, compare to census claims; optional `doc_frame_cue` on video path.

**Independent Test**: Upload clear ID in active session → readable extraction → name/DOB consistency result stored; unreadable image offers retry or review.

### Implementation for User Story 3

- [X] T050 [P] [US3] Implement document evidence schemas in `shared/schemas/document_evidence.py`
- [X] T051 [US3] Implement `doc_frame_cue` plugin in `services/video/plugins/doc_frame_cue.py` and extend registry started in T037 in `services/video/registry.py` (depends on T037; do not parallelize with T037)
- [X] T052 [US3] Implement Sarvam document digitization client (with fake/offline mode) in `services/document/sarvam_digitize.py`
- [X] T053 [US3] Implement field normalization + name/DOB (or age) consistency checker in `services/document/field_matcher.py`
- [X] T054 [US3] Implement Telegram document capture handler saving media and invoking document service in `apps/telegram/handlers/document_capture.py`
- [X] T055 [US3] Attach document evidence + match scores to session in `apps/telegram/handlers/document_capture.py` via `apps/api/db/session_store.py`
- [X] T056 [US3] Map unreadable/wrong-type document to retry or needs-review status in `apps/telegram/handlers/document_capture.py`
- [X] T057 [US3] Ensure `SHOW_ID_AND_READ_FIELD` jobs include `document_field` + `document_visible` targets via `apps/telegram/services/job_builder.py`

**Checkpoint**: US3 independently produces document consistency evidence on a session that has census profile

---

## Phase 5b: AWS Bedrock & Kognition Video API Integration

**Purpose**: Wire AWS Bedrock (LLM verdict explanation) and Kognition (cloud video liveness/face analysis) into the pipeline as optional, configurable backends.

**Dependencies**: Phase 2 complete (schemas + registry); `.env` credentials file populated.

**Credential file**: `.env` (copy from `.env.example` at repo root); never commit `.env`.

- [X] T_B1 Add `services/orchestrator/bedrock_client.py`: thin boto3 Bedrock Runtime wrapper; reads `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `BEDROCK_MODEL_ID` from env; exposes `invoke(prompt: str) -> str` with structured-JSON mode
- [X] T_B2 [P] Implement `services/orchestrator/verdict_explainer.py`: uses BedrockClient to produce a JSON explanation payload bound to `EvidenceBundle`; falls back to deterministic summary if `BEDROCK_MODEL_ID` not set (offline mode); satisfies T061
- [X] T_K1 [P] Implement `services/video/plugins/kognition_liveness.py`: Kognition API client plugin (reads `KOGNITION_API_KEY`, `KOGNITION_BASE_URL` from env); sends frame/image bytes to Kognition liveness endpoint; parses response into `PluginResult` scores (`face_count`, `spoof_score`, `liveness_score`); falls back to offline stub when key absent
- [X] T_K2 Register `kognition_liveness` plugin in `services/video/registry.py` default profile (after T_K1); wire into `__init__.py` imports
- [X] T_B3 Add `services/orchestrator/__init__.py` and `services/orchestrator/finalize.py` stub combining policy verdict + BedrockClient explanation; satisfies T062 prerequisite

---

## Phase 6: User Story 4 - Receive an Explainable Enrollment Decision (Priority: P4)

**Goal**: Fuse evidence with deterministic policy; return approved/review/rejected/needs-more-evidence with reasons in Telegram; operator-readable summary.

**Independent Test**: Finalize session with evidence (or fixtures) → user sees verdict + reason; operator view lists challenge outcomes without raw logs.

### Implementation for User Story 4

- [X] T058 [P] [US4] Implement enrollment verdict schema in `shared/schemas/decision.py` (`approved` | `needs_review` | `rejected` | `needs_more_evidence`)
- [X] T059 [P] [US4] Implement typed `EvidenceBundle` aggregating `VideoEvidence` + `SpeechEvidence` + `DocumentEvidence` in `shared/schemas/evidence_bundle.py` (FR-009)
- [X] T060 [US4] Implement deterministic policy fusion (weights/thresholds/hard-fails; LLM not sole authority) consuming `EvidenceBundle` in `services/policy/verdict.py` (depends on T059)
- [X] T061 [P] [US4] Implement Bedrock-backed explanation summarizer (structured JSON only, evidence-bound) in `services/orchestrator/verdict_explainer.py`
- [X] T062 [US4] Implement finalize flow combining policy verdict + explanation using `EvidenceBundle` in `services/orchestrator/finalize.py` (depends on T059, T060)
- [X] T063 [US4] Add `POST /sessions/{session_id}/finalize` in `apps/api/routes/sessions.py`
- [X] T064 [US4] Add `GET /sessions/{session_id}` operator summary (evidence ids, reason codes, per-challenge outcomes) in `apps/api/routes/sessions.py`
- [X] T065 [US4] Implement Telegram finalize + outcome message handler in `apps/telegram/handlers/finalize.py`
- [X] T066 [US4] Persist final enrollment verdict and evidence references on session in `apps/api/db/session_store.py` (extend as needed)

**Checkpoint**: End-to-end enrollment verdict explainable in Telegram; operator GET works

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Local DX, privacy hygiene, quickstart validation, session expiry

- [X] T067 [P] Align `README.md` with local run order (API, video worker, Telegram bot) and link `specs/001-telegram-kyc-census/quickstart.md`
- [X] T068 [P] Add sample `evidence/demo/job.json` template (no real PII photos) per quickstart in `evidence/demo/job.json.example`
- [X] T069 Run quickstart smoke: `GET /video/plugins`, `POST /video/verify` with fixture, confirm `document_field` → `deferred`; manually note timing against SC-001/SC-005 demo targets in `specs/001-telegram-kyc-census/quickstart.md` checklist
- [X] T070 Add media retention note and optional cleanup helper in `shared/utils/evidence_cleanup.py`
- [X] T071 Verify error paths (missing media, unknown plugin, consent decline, multi-face) return user-visible messages in `apps/telegram/handlers/` and API error handlers in `apps/api/main.py`
- [X] T072 Implement 24h abandoned-session expiry → `needs_more_evidence` (or closed) in `apps/api/db/session_store.py` and resume rules in `apps/telegram/handlers/start.py` per spec Assumptions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Foundational — no dependency on US2–US4
- **US2 (Phase 4)**: Depends on Foundational; integrates with US1 session (can use API-seeded session for independent test)
- **US3 (Phase 5)**: Depends on Foundational; needs census profile claims (US1 or seeded); T051 after T037
- **US4 (Phase 6)**: Depends on Foundational; needs evidence from US2/US3 (or fixture evidence); T060/T062 after T059
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 only — **suggested MVP stop**
- **US2 (P2)**: After Phase 2; uses US1 session in bot path; video layer independently testable via `POST /video/verify`
- **US3 (P3)**: After Phase 2; claim fields from US1; registry extend after T037
- **US4 (P4)**: After Phase 2; fuses US2+US3 evidence when present via `EvidenceBundle`

### Within Each User Story

- Schemas before services (`SpeechEvidence` before phrase verifier; `EvidenceBundle` before policy/finalize)
- Plugins/services before Telegram handlers
- Handlers before finalize/operator views
- Story complete before next priority when staffing is serial

### Parallel Opportunities

- T002–T004 in Setup
- T006–T008 schemas in Foundational **after T005** (not T015 — depends on T014)
- T029–T036 video plugins in parallel
- T045–T046 speech schema + STT client in parallel
- T050 parallel at start of US3; T051 serial after T037
- T058–T059 and T061 parallel at start of US4 (T060 after T059)
- T067–T068 in Polish

---

## Parallel Example: User Story 2

```bash
# Plugins in parallel (different files):
Task: "Implement face_detector in services/video/plugins/face_detector.py"
Task: "Implement frame_quality in services/video/plugins/frame_quality.py"
Task: "Implement pose_estimator in services/video/plugins/pose_estimator.py"
Task: "Implement spoof_detector in services/video/plugins/spoof_detector.py"

# Speech schema + STT in parallel:
Task: "SpeechEvidence in shared/schemas/speech_evidence.py"
Task: "Sarvam STT adapter in services/speech/sarvam_stt.py"

# After plugins land:
Task: "Wire registry + scoring + pipeline completion"
Task: "Telegram presence handlers + job_builder"
```

---

## Parallel Example: User Story 1

```bash
Task: "i18n messages in apps/telegram/i18n/messages.py"
Task: "challenge_plan stub in services/policy/challenge_plan.py"
# Then sequential handlers: bot → start → consent → census (all using i18n)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup
2. Phase 2: Foundational (schemas, session store, video stubs, API)
3. Phase 3: US1 Telegram census capture
4. **STOP and VALIDATE** US1 independent test
5. Demo consent + census Q&A on Telegram

### Incremental Delivery

1. Setup + Foundational → `/video/verify` stub live
2. US1 → Telegram census MVP
3. US2 → Pluggable video + typed speech evidence + challenges (plan focus)
4. US3 → Document consistency
5. US4 → `EvidenceBundle` + deterministic enrollment verdict + explanations
6. Polish → quickstart green + 24h expiry on Linux/macOS

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then: Dev A = US1 Telegram; Dev B = US2 video plugins; Dev C = US3 document client
3. US4 integrates evidence branches via `EvidenceBundle`

---

## Notes

- [P] = different files, no incomplete dependencies
- [USn] maps to spec user stories for traceability
- Video layer contracts: `contracts/verification-job.md`, `video-evidence.md`, `video-api.md`
- `document_field` targets stay `deferred` in video scoring; OCR only in `services/document/`
- Analysis remediations (2026-07-26): speech schema (H1), T015 deps (H2), i18n wiring (M1), census_guide stub scope (M2), session expiry (M3), no orphan `challenge.py` (M4), `EvidenceBundle` (M5), multi-face UX (M6)
- Commit after each task or logical group
- Avoid: untyped boundary dicts, LLM-only final verdicts, Windows-only scripts
