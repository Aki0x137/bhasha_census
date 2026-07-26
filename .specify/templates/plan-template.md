# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+ (typed) [or NEEDS CLARIFICATION if feature differs]

**Primary Dependencies**: pip; Temporal; LangGraph; FastAPI; Pydantic shared schemas; Sarvam; AWS Bedrock; OpenCV/MediaPipe as needed

**Storage**: SQLite (session metadata) + local `evidence/` filesystem [S3 only if cloud mode justified]

**Testing**: pytest (unit/policy/schema); integration for Temporal activities & adapters; e2e for challenge branches when in scope

**Target Platform**: Linux and macOS local developer runtime (MVP)

**Project Type**: Local-first web + API + Temporal workers (liveness verification MVP)

**Performance Goals**: [domain-specific, e.g., interactive challenge latency, or NEEDS CLARIFICATION]

**Constraints**: MVP-only scope; typed contracts at all boundaries; deterministic policy owns final verdict; dual-OS (Linux/macOS) local run

**Scale/Scope**: Single-machine MVP; not production identity proofing [refine per feature]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify against `.specify/memory/constitution.md` (Bhasaha Census Constitution):

- [ ] **MVP-only**: Change maps to MVP acceptance criteria; no out-of-scope production/biometric/fraud-graph work
- [ ] **Linux/macOS local-first**: Feature remains runnable locally on Linux or macOS (cloud APIs allowed)
- [ ] **Typed contracts**: Cross-service/API payloads use shared type-safe Python schemas (no untyped boundary dicts)
- [ ] **Layered architecture**: Extraction, scoring, and decision stay separated; services stateless except session store
- [ ] **Deterministic final authority**: Policy engine owns PASS/REVIEW/FAIL; LangGraph/Bedrock are not sole source of truth
- [ ] **Multi-signal evidence**: Verdict fuses independent branches with reason codes and evidence ids
- [ ] **Privacy/observability**: Consent, retention, redaction, and structured session/challenge logging addressed if media/PII touched
- [ ] **Stack alignment**: Python + pip + Temporal + LangGraph (and documented MVP deps) unless Complexity Tracking justifies an exception

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Prefer the MVP layout below (constitution + docs/liveliness_check_mvp.md).
  Expand with real paths for this feature; remove unused branches. Do not leave Option labels.
-->

```text
apps/
├── web/                 # React/Next.js client (webcam, mic, challenges)
└── api/                 # FastAPI session/challenge API
services/
├── video/               # face/liveness/spoof workers
├── speech/              # Sarvam STT integration
├── document/            # Sarvam document digitization
├── orchestrator/        # LangGraph + Bedrock aggregation
└── policy/              # deterministic verdict rules
shared/
├── schemas/             # type-safe Python contracts (Pydantic)
├── utils/
└── prompts/
infra/
├── local/               # Temporal, local run scripts (Linux/macOS)
└── aws/                 # optional cloud mode later
tests/
├── unit/
├── integration/
└── e2e/
evidence/                # local evidence snapshots (gitignored in real use)
docs/
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
