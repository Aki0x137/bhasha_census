<!--
Sync Impact Report
- Version change: (uninitialized template) → 1.0.0
- Modified principles: placeholders → I–V concrete principles (initial ratification)
- Added sections: Technology Stack & Architecture; Security, Privacy & Quality Gates
- Removed sections: none (template placeholders replaced)
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated
  - .specify/templates/spec-template.md ✅ updated
  - .specify/templates/tasks-template.md ✅ updated
  - .specify/templates/commands/*.md ⚠ N/A (directory absent)
  - README.md ✅ updated (project pointer)
  - docs/liveliness_check_mvp.md ✅ referenced as runtime guidance (no principle conflicts)
- Follow-up TODOs: none
-->

# Bhasaha Census Constitution

## Core Principles

### I. MVP-Only Scope Discipline

This repository exists solely to deliver a locally runnable MVP for
video liveness and human-vs-AI media verification. Features MUST map to
the four MVP questions in `docs/liveliness_check_mvp.md`: live human face
presence, real-time challenge response, AI/replay manipulation risk, and
document consistency with spoken answers. Work that belongs in production
identity proofing, government-grade biometric compliance, fraud-graph
analytics, continuous post-session monitoring, or custom model training
MUST be rejected or deferred. Every PR and plan MUST state how the change
advances an MVP acceptance criterion.

**Rationale**: Scope creep kills hackathon/MVP delivery. Explicit
non-goals keep agents and humans aligned on shippable value.

### II. Cross-Platform Local-First Runtime

The MVP MUST run on developer machines using **Linux or macOS** without
requiring cloud-only infrastructure for the happy path. Local layout MUST
support: frontend on localhost, API, Temporal workers, SQLite metadata,
and a filesystem `evidence/` store. Cloud services (Sarvam, AWS Bedrock)
MAY be called over the network, but session orchestration, evidence
persistence, and local workers MUST remain runnable offline-capable
except for those external API calls. Platform-specific code MUST be
avoided or isolated behind thin adapters; scripts and docs MUST work on
both Linux and macOS (POSIX shell preferred).

**Rationale**: Dual-OS local DX is a hard product constraint; Windows is
out of scope for MVP runtime support.

### III. Typed Contract Surfaces (NON-NEGOTIABLE)

All cross-service and API payloads MUST be defined with **type-safe
Python** contracts (Pydantic models or equivalent typed schemas) under a
shared package (e.g. `shared/schemas/`). JSON Schema or OpenAPI MUST be
derived from those types, not hand-duplicated. Session, challenge,
evidence, verdict, and worker message shapes MUST be versioned and
validated at process boundaries. Untyped `dict` payloads at service
boundaries are forbidden except inside ephemeral adapters that
immediately parse into typed models.

**Rationale**: Typed contracts catch integration bugs early and keep
Temporal/LangGraph workflows, FastAPI routes, and workers coherent.

### IV. Layered Evidence Architecture

Services MUST stay **stateless except session persistence**. Extraction,
scoring, and decision MUST be separate layers. Video, speech, and
document branches MUST produce typed evidence objects with scores and
`payload_ref`s; the orchestrator aggregates them. Challenge generation
MUST be deterministic under a test seed. Raw model outputs MUST be
recorded before post-processing. Session state transitions MUST be
monotonic (`CREATED` → … → `COMPLETED`), with retries only inside
challenge states.

**Rationale**: Separation of concerns makes branches independently
testable and prevents entangled “god services.”

### V. Multi-Signal Fusion & Deterministic Final Authority

The system MUST NOT rely on a single signal. Verdicts MUST fuse presence,
challenge, speech, document, deepfake, and replay evidence into
`PASS | REVIEW | FAIL | NEEDS_MORE_EVIDENCE` with reason codes. A
**deterministic policy engine** owns the final pass/fail decision.
LangGraph/Bedrock MAY summarize, generate challenges, or recommend;
they MUST NOT be the only source of truth. Hard-fail rules (no face after
grace, challenge timeout, mandatory phrase mismatch, unreadable document,
critical spoof score) MUST short-circuit to FAIL or REVIEW per policy,
independent of model prose.

**Rationale**: Explainable, replayable decisions require rules over
unbounded LLM judgment.

## Technology Stack & Architecture

### Required stack

| Concern | Choice |
|---------|--------|
| Language | Python 3.11+ (typed) |
| Package management | **pip** (+ `requirements.txt` / lockfile as adopted) |
| Workflow engine | **Temporal** for durable session/challenge workflows |
| Agent/graph orchestration | **LangGraph** for evidence aggregation and Bedrock-facing graphs |
| API | FastAPI (Python) preferred for the backend |
| Contracts | Pydantic (or equivalent) shared schemas |
| Speech / documents | Sarvam Streaming STT + Document Digitization |
| LLM / guardrails | AWS Bedrock (model call first; Agents later) |
| Video heuristics | OpenCV + MediaPipe (or equivalent) local workers |
| Metadata store | SQLite for MVP |
| Object/evidence store | Local filesystem `evidence/` (S3 only in cloud mode) |
| Frontend | React or Next.js webcam/mic client |

### Architecture mandates

- Prefer the repo layout in `docs/liveliness_check_mvp.md` §10
  (`apps/`, `services/`, `shared/`, `infra/local/`, `tests/`, `evidence/`).
- Temporal workflows own long-running session lifecycle; activities wrap
  video/speech/document/Bedrock calls.
- LangGraph graphs MUST consume/produce typed shared schemas.
- Default PASS policy: at least one active physical challenge, one speech
  challenge, and one document challenge succeed, and no high-confidence
  spoof signal.
- Scoring weights and thresholds in the MVP doc are the starting policy;
  changes MUST be documented and test-covered.

### Explicit non-goals (MVP)

Production IdP, certified biometrics, large-scale fraud graphs, always-on
monitoring after session end, and training custom deepfake models from
scratch are out of scope.

## Security, Privacy & Quality Gates

### Privacy & consent

- Explicit consent UI MUST precede camera and microphone capture.
- Raw video MUST NOT be retained longer than needed for MVP debugging;
  prefer scores, snapshots, and references.
- Document text not required for verification MUST be redacted from
  long-lived stores.
- Prompts and transcripts MUST remain session-scoped.
- Every verdict MUST reference traceable evidence ids.

### Observability

Structured logs MUST capture session lifecycle, challenge timestamps,
Sarvam/Bedrock request ids, per-branch latency, and final verdict with
reason codes. Errors listed in the MVP doc (permissions, API timeouts,
invalid streams, multiple faces, unanswered prompts, Bedrock failures)
MUST have explicit handlers: retry once for transient faults, otherwise
downgrade to REVIEW and retain evidence for manual review.

### Testing & simplicity

- Prefer unit tests for policy and schema validation; integration tests
  for Temporal activities and Sarvam/Bedrock adapters (with fakes when
  offline); e2e for the three challenge branches when feasible.
- YAGNI: do not add infrastructure, abstractions, or cloud modes that
  are not required to meet MVP acceptance criteria.
- Complexity that violates these principles MUST be justified in the plan
  Complexity Tracking table.

## Governance

This constitution supersedes informal practice and conflicting draft notes
when they disagree on scope, stack, or decision authority. Runtime product
guidance lives in `docs/liveliness_check_mvp.md`; when that doc and this
constitution conflict on governance (MUST rules), the constitution wins
and the doc MUST be updated in the same change set.

Amendments:

1. Propose the change with rationale and impact on plans/specs/tasks.
2. Bump **CONSTITUTION_VERSION** using semver: MAJOR for removed/redefined
   principles, MINOR for new principles or material expansions, PATCH for
   clarifications.
3. Set **Last Amended** to the amendment date (ISO `YYYY-MM-DD`).
4. Propagate updates to Spec Kit templates and active feature plans.

Compliance:

- `/speckit-plan` Constitution Check MUST pass before Phase 0 research
  proceeds beyond documented exceptions.
- Reviews and implementation tasks MUST verify typed contracts, Linux/macOS
  local runnability, multi-signal policy ownership, and MVP scope.
- Unjustified complexity, untyped boundary payloads, or LLM-only verdicts
  are compliance failures.

**Version**: 1.0.0 | **Ratified**: 2026-07-26 | **Last Amended**: 2026-07-26
