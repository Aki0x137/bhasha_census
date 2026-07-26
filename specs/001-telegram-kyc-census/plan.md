# Implementation Plan: Pluggable Video Verification Layer

**Branch**: `001-telegram-kyc-census` | **Date**: 2026-07-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-telegram-kyc-census/spec.md`,
plus planning focus: build a **pluggable video layer** that accepts
**document/field verification targets** and **runtime params** to evaluate
during presence/liveness challenges (Telegram KYC/census MVP).

**Note**: This plan is produced by `/speckit-plan`. Phase 0–1 artifacts live
alongside this file.

## Summary

Deliver a **channel-agnostic, pluggable video verification package** under
`services/video/` that:

1. Accepts a typed **VerificationJob** (media refs + challenge params +
   optional document/field expectations to check in-frame or against session
   claims).
2. Runs a pipeline of swappable plugins (face detect/track, quality, pose/
   blink/mouth heuristics, spoof/replay scores, optional doc-in-frame cues).
3. Emits typed **VideoEvidence** for Temporal activities and the
   deterministic policy engine—never a sole LLM verdict.

Telegram (and later other clients) only supply media and params; they do not
embed OpenCV/MediaPipe logic. Document OCR remains in `services/document/`;
the video layer consumes **declared verification params** (which fields/
thresholds/challenges matter) so the same job schema drives presence checks
aligned with KYC/census claims.

## Technical Context

**Language/Version**: Python 3.11+ (typed)

**Primary Dependencies**: pip; Pydantic v2 schemas; OpenCV; MediaPipe (or
equivalent face landmarks); Temporal (activity wrapper); optional NumPy;
pytest. LangGraph/Bedrock/Sarvam are **consumers/siblings**, not inside the
video plugin core.

**Storage**: Job metadata via caller/session store (SQLite upstream); raw/
derived frames under `evidence/{session_id}/video/`; video service itself is
stateless.

**Testing**: pytest unit tests for schemas, plugin registry, and scoring
pure functions; integration tests with fixture images/short clips; fake
plugins for Temporal activity contracts.

**Target Platform**: Linux and macOS local developer runtime (MVP)

**Project Type**: Pluggable library + Temporal activity worker within the
local-first KYC/census platform (Telegram channel adapter separate)

**Performance Goals**: Process a single challenge clip/photo set in ≤10s on a
typical laptop CPU for MVP demos; fail fast (<2s) on unreadable/no-face input

**Constraints**: MVP-only; typed contracts at all boundaries; extraction →
scoring → decision separation; deterministic policy owns final enrollment
verdict; dual-OS (Linux/macOS); no custom deepfake model training

**Scale/Scope**: Single-machine MVP; one VerificationJob at a time per worker
process for demos; not production biometric certification

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify against `.specify/memory/constitution.md` (Bhasaha Census Constitution):

- [x] **MVP-only**: Maps to presence/liveness + evidence for KYC/census MVP
  (spec US2); no certified biometrics or fraud graphs
- [x] **Linux/macOS local-first**: OpenCV/MediaPipe local workers; no
  Windows requirement
- [x] **Typed contracts**: `shared/schemas` Pydantic models for job in/out
- [x] **Layered architecture**: Plugins extract → scorer aggregates → policy
  (outside video package) decides; service stateless
- [x] **Deterministic final authority**: Video layer emits scores/reason
  codes only; policy/LangGraph must not be sole authority inside this layer
- [x] **Multi-signal evidence**: Video evidence is one branch; params may
  reference document fields but OCR stays in document service
- [x] **Privacy/observability**: Evidence refs + structured logs; minimal raw
  retention guidance in quickstart
- [x] **Stack alignment**: Python + pip + Temporal activity; OpenCV/MediaPipe
  per constitution

**Post-design re-check**: Pass. Telegram-as-primary-channel vs constitution’s
React client example is scoped to adapters (see Complexity Tracking)—video
core remains channel-agnostic.

## Project Structure

### Documentation (this feature)

```text
specs/001-telegram-kyc-census/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
apps/
├── telegram/            # Bot adapter: maps Telegram media → VerificationJob
└── api/                 # FastAPI: session + optional POST /video/verify for local demos
services/
├── video/               # ★ Pluggable video verification layer (this plan focus)
│   ├── __init__.py
│   ├── pipeline.py      # Orchestrates plugins for one VerificationJob
│   ├── registry.py      # Plugin discovery/registration
│   ├── plugins/         # face_detector, face_tracker, frame_quality, ...
│   ├── scoring.py       # Aggregate plugin outputs → VideoEvidenceScores
│   └── activity.py      # Temporal activity entrypoint
├── speech/              # Sarvam STT (sibling; not in this slice)
├── document/            # Sarvam digitization (sibling; supplies field expectations)
├── orchestrator/        # LangGraph + Bedrock
└── policy/              # Deterministic verdict rules
shared/
├── schemas/
│   ├── verification_job.py   # Job input: media, ChallengeParams, targets
│   ├── video_evidence.py     # Video job output evidence
│   ├── speech_evidence.py    # Speech challenge evidence (typed boundary)
│   ├── document_evidence.py  # Document OCR / match evidence
│   ├── evidence_bundle.py    # Aggregates video+speech+document for policy
│   ├── session.py            # EnrollmentSession, CensusProfile
│   ├── decision.py           # Enrollment verdict enum + payload
│   └── common.py             # session ids, enums, reason codes
├── utils/
└── prompts/
infra/
├── local/               # Temporal, pip install, run-video-worker.sh
└── aws/
tests/
├── unit/
│   └── video/
├── integration/
│   └── video/
└── e2e/
evidence/
docs/
```

**Structure Decision**: Implement the pluggable video layer first as
`services/video/` + `shared/schemas/{verification_job,video_evidence}.py`.
Telegram/API adapters call the same Temporal activity. Document OCR stays in
`services/document/`; verification **params** (which fields/thresholds to
enforce) travel on the VerificationJob so video and policy stay aligned
without merging services. Speech and document branches each have typed
evidence schemas; `EvidenceBundle` feeds deterministic policy for the
enrollment verdict. `ChallengeParams` live inside `verification_job.py`
(no separate `challenge.py`).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Telegram adapter (`apps/telegram`) instead of constitution’s React/Next example | Spec mandates Telegram as MVP channel | Browser-only client would ignore accepted spec; video core stays channel-agnostic |
| Plugin registry abstraction | User-requested pluggable video layer; swap heuristics without rewriting pipeline | Hard-coded OpenCV script blocks iterative detector swaps and tests with fakes |

---

## Phase 0 & Phase 1

See `research.md`, `data-model.md`, `contracts/`, and `quickstart.md` in this
directory.
