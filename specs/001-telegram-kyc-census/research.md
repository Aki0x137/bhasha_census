# Research: Pluggable Video Verification Layer

**Feature**: `001-telegram-kyc-census`  
**Date**: 2026-07-26

## R1. Pluggable video architecture

**Decision**: Use a **plugin Protocol + registry** inside `services/video/`.
Each plugin implements `run(ctx: VideoPluginContext) -> PluginResult` with a
stable name, version, and declared capability tags (`face`, `quality`,
`liveness`, `spoof`, `doc_frame`). A linear **pipeline** runs enabled plugins
listed on the VerificationJob (or a default profile), then `scoring.py`
maps results into typed `VideoEvidenceScores`.

**Rationale**: Constitution requires separable extraction vs scoring;
MVP needs fake plugins for offline tests; OpenCV/MediaPipe detectors will
iterate quickly.

**Alternatives considered**:

- Monolithic `analyze_video()` script — rejected (not pluggable, hard to test).
- Heavy plugin framework (stevedore/pluggy with entry points) — deferred;
  in-process registry is enough for MVP.
- Microservice-per-detector — rejected (YAGNI for local MVP).

## R2. Job input: docs + params to verify

**Decision**: Define `VerificationJob` with three input groups:

1. **Media**: `media_refs[]` (local paths or evidence keys), `media_kind`
   (`photo` | `video_clip` | `frame_sequence`).
2. **Challenge params**: `challenge_type`, `prompt_text`, `time_limit_ms`,
   `min_confidence`, `max_attempts`, `seed` (deterministic under tests),
   thresholds overrides (`quality_min`, `spoof_max`, `face_required`, etc.).
3. **Verification targets** (`targets`): structured list of what must be
   corroborated during/after the video path, e.g. expected pose/action,
   optional `document_fields_expected` (name, dob) as **claims for later
   policy/doc service**, and flags like `require_face`, `require_single_face`,
   `check_doc_visible_in_frame` (heuristic only in MVP).

The video layer **does not** call Sarvam OCR. It may set
`doc_visible_score` heuristics; field matching is policy + document service.

**Rationale**: User asked for a layer that takes “inputs for docs and params
which need to be verified during the process.” Putting both on one typed job
keeps Temporal activities and Telegram adapters simple.

**Alternatives considered**:

- Separate APIs for video vs “verification config” — rejected for MVP
  (extra round-trips, sync bugs).
- Embedding full document images into video plugins for OCR — rejected
  (violates layered architecture; duplicates document service).

## R3. Default plugin set (MVP)

**Decision**: Ship these plugins (heuristics OK):

| Plugin | Role |
|--------|------|
| `face_detector` | Face present / count |
| `face_tracker` | Stability across frames (clips) |
| `frame_quality` | Blur/brightness/size score |
| `pose_estimator` | Coarse head pose for LOOK_LEFT/RIGHT etc. |
| `blink_detector` | Optional blink cues when enough frames |
| `mouth_movement_detector` | Weak liveness cue |
| `spoof_detector` | Lightweight heuristic / placeholder score |
| `temporal_anomaly_detector` | Replay/freeze hints on clips |
| `doc_frame_cue` (optional) | Rough “card-like rectangle” presence |

**Rationale**: Aligns with `docs/liveliness_check_mvp.md` video submodules
without training custom models.

**Alternatives considered**: Commercial face SDK — deferred (cost, OS
packaging). Deep learning spoof CNN — out of constitution non-goals.

## R4. Temporal integration

**Decision**: Expose `analyze_verification_job(job: VerificationJob) ->
VideoEvidence` as a Temporal **activity** in `services/video/activity.py`.
Workflows (enrollment) remain outside this package. Activity validates
Pydantic input, runs pipeline, writes optional debug snapshots under
`evidence/`, returns typed evidence.

**Rationale**: Constitution mandates Temporal for durable session work;
keeps video workers restartable.

**Alternatives considered**: Sync-only FastAPI without Temporal — acceptable
for unit demos via `/video/verify`, but enrollment path should still use
activities when session workflow exists.

## R5. Channel adapters

**Decision**: Telegram bot downloads photo/voice/video to `evidence/`, builds
`VerificationJob` from challenge plan + census claim params, calls activity
or API. FastAPI `POST /video/verify` supports local curl demos without
Telegram.

**Rationale**: Spec is Telegram-first; constitution React client is not
required for this slice.

**Alternatives considered**: Browser webcam streaming WebRTC into video
worker — deferred (out of spec MVP channel).

## R6. Scoring & reason codes

**Decision**: Aggregate plugin floats/bools into:

- `face_present`, `track_stable`, `quality_score`, `motion_score`,
  `spoof_score`, `replay_score`, optional `doc_visible_score`
- `reason_codes[]` such as `FACE_PRESENT`, `FACE_MISSING`, `MULTI_FACE`,
  `QUALITY_LOW`, `SPOOF_SUSPECT`, `CHALLENGE_POSE_OK`, `DOC_FRAME_WEAK`
- `plugin_results[]` raw per-plugin payloads (typed union / JSON-able dict
  bounded by schema) for operator review

Hard fail recommendations (`hard_fail_hint: bool`) may be set by scoring
rules (e.g. no face); **policy service** still owns final enrollment
verdict.

**Rationale**: Multi-signal fusion + deterministic authority.

## R7. Dependencies & packaging

**Decision**: `requirements-video.txt` (or extras section) with `opencv-python-headless`,
`mediapipe`, `numpy`, `pydantic`, `temporalio` for the worker. Prefer
headless OpenCV for Linux/macOS servers without GUI.

**Rationale**: Dual-OS local DX; headless avoids GUI deps in CI.

**Alternatives considered**: `opencv-python` (GUI) — unnecessary for workers.

## Resolved clarifications

| Topic | Resolution |
|-------|------------|
| NEEDS CLARIFICATION on performance | ≤10s/job laptop CPU; <2s fail-fast no-face |
| Doc verification inside video? | Params/claims on job; OCR in document service |
| Plugin mechanism | In-process Protocol + registry for MVP |

All Technical Context unknowns for this slice are resolved.
