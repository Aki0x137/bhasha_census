# Data Model: Pluggable Video Verification

**Feature**: `001-telegram-kyc-census`  
**Date**: 2026-07-26  
**Focus**: Verification jobs, params/targets, video evidence, plugin results

## Entity overview

```text
EnrollmentSession (upstream)
    └── ChallengePlan
            └── VerificationJob ──► VideoEvidence
                    ├── MediaRef[]
                    ├── ChallengeParams
                    ├── VerificationTarget[]
                    └── (pipeline) PluginResult[]
```

## EnrollmentSession (upstream, reference)

Owned by session/API layer; video layer only receives `session_id`.

| Field | Type | Notes |
|-------|------|-------|
| session_id | string | Stable id, e.g. `sess_...` |
| user_ref | string \| null | Telegram user id or external ref |
| status | enum | Monotonic session states per spec |
| census_profile | object | name, dob_or_age, gender, locality, household_size |
| consent_accepted | bool | Must be true before media jobs |

## ChallengeParams

| Field | Type | Validation |
|-------|------|------------|
| challenge_id | string | Required |
| challenge_type | enum | See below |
| prompt_text | string | Shown to user / logged |
| expected_response | string \| null | Pose label or phrase hint |
| time_limit_ms | int | > 0 |
| min_confidence | float | 0..1 |
| max_attempts | int | ≥ 1 |
| seed | int \| null | Deterministic challenge/plugin jitter under test |
| quality_min | float \| null | Override default |
| spoof_max | float \| null | Override default |
| enabled_plugins | string[] \| null | Subset of registry; null = profile default |

### challenge_type (MVP)

- `LOOK_LEFT_RIGHT`
- `BLINK_TWICE`
- `SMILE_AND_TILT`
- `SAY_RANDOM_PHRASE` (video may only check mouth motion; speech service owns transcript)
- `SHOW_ID_AND_READ_FIELD` (video may run `doc_frame_cue`; document service owns OCR)
- `CUSTOM` (params-driven)

## VerificationTarget

Declares **what must be verified** during the process (docs + params).

| Field | Type | Validation |
|-------|------|------------|
| target_id | string | Required |
| kind | enum | `presence` \| `pose` \| `liveness_cue` \| `document_field` \| `document_visible` \| `anti_spoof` |
| field_name | string \| null | e.g. `full_name`, `date_of_birth` for document_field |
| expected_value | string \| null | Claim from census profile (comparison often outside video) |
| required | bool | If true, failure contributes hard_fail_hint / reason |
| weight | float | 0..1 relative importance for scoring hints |
| metadata | object | Free-form bounded dict (max depth 2) for plugin hints |

**Rules**:

- `document_field` targets MUST NOT be OCR’d by video plugins; they travel for
  policy/document alignment and logging.
- `document_visible` MAY be scored by `doc_frame_cue`.
- At least one `presence` or pose/liveness target SHOULD be present for
  physical challenges.

## MediaRef

| Field | Type | Validation |
|-------|------|------------|
| media_id | string | Required |
| uri | string | Local path or evidence key |
| kind | enum | `photo` \| `video_clip` \| `frame_sequence` |
| captured_at_ms | int \| null | Client timestamp |
| content_type | string \| null | e.g. `image/jpeg` |

## VerificationJob

| Field | Type | Validation |
|-------|------|------------|
| job_id | string | Required |
| session_id | string | Required |
| media | MediaRef[] | Min length 1 |
| params | ChallengeParams | Required |
| targets | VerificationTarget[] | Default empty list allowed; profile may inject |
| locale | string | Default `en-IN` |
| created_at_ms | int | Required |

**State**: Jobs are effectively single-shot (`queued` → `running` →
`completed` | `failed`). No long-lived job state inside the video worker
beyond the activity execution.

## PluginResult

| Field | Type | Notes |
|-------|------|-------|
| plugin_name | string | Registry key |
| plugin_version | string | Semver string |
| ok | bool | Plugin ran without internal error |
| scores | object | Plugin-specific floats/bools |
| labels | string[] | Short tags |
| error_message | string \| null | If !ok |
| duration_ms | int | Timing |

## VideoEvidenceScores

| Field | Type | Range / notes |
|-------|------|---------------|
| face_present | bool | |
| face_count | int | ≥ 0 |
| track_stable | bool | |
| quality_score | float | 0..1 |
| motion_score | float | 0..1 |
| spoof_score | float | 0..1 higher = more suspicious |
| replay_score | float | 0..1 |
| doc_visible_score | float \| null | 0..1 if evaluated |
| pose_match_score | float \| null | Against expected pose |
| hard_fail_hint | bool | Scoring recommendation only |

## VideoEvidence

| Field | Type | Notes |
|-------|------|-------|
| evidence_id | string | `ev_...` |
| job_id | string | |
| session_id | string | |
| type | literal | `video` |
| timestamp_ms | int | |
| source | literal | `worker` |
| payload_ref | string \| null | Debug snapshot path |
| scores | VideoEvidenceScores | |
| reason_codes | string[] | |
| plugin_results | PluginResult[] | |
| targets_evaluation | TargetEvaluation[] | Per-target pass/fail/skip |

## SpeechEvidence

Typed boundary for speech challenge results (constitution Principle III).

| Field | Type | Notes |
|-------|------|-------|
| evidence_id | string | `ev_...` |
| session_id | string | |
| challenge_id | string | |
| type | literal | `speech` |
| timestamp_ms | int | |
| transcript | string | Normalized STT text |
| confidence | float | 0..1 |
| latency_ms | int | Response latency |
| keyword_match_score | float | 0..1 |
| phrase_match_score | float | 0..1 |
| reason_codes | string[] | e.g. `SPEECH_MATCH_OK`, `SPEECH_MISMATCH` |
| payload_ref | string \| null | Audio evidence path |

## DocumentEvidence

| Field | Type | Notes |
|-------|------|-------|
| evidence_id | string | |
| session_id | string | |
| type | literal | `document` |
| timestamp_ms | int | |
| document_text | string \| null | Extracted text |
| detected_fields | object | Normalized field map |
| document_quality_score | float | 0..1 |
| document_match_score | float | 0..1 vs census claims |
| reason_codes | string[] | |
| payload_ref | string \| null | Image path |

## EvidenceBundle

Aggregation consumed by deterministic policy / finalize (FR-009).

| Field | Type | Notes |
|-------|------|-------|
| session_id | string | |
| video | VideoEvidence[] | May be empty |
| speech | SpeechEvidence[] | May be empty |
| document | DocumentEvidence[] | May be empty |
| collected_at_ms | int | |

## EnrollmentVerdict

Product term “enrollment decision” ≡ this verdict payload.

| Field | Type | Notes |
|-------|------|-------|
| session_id | string | |
| verdict | enum | `approved` \| `needs_review` \| `rejected` \| `needs_more_evidence` |
| confidence | float | 0..1 |
| reason_codes | string[] | |
| next_action | enum | `allow` \| `manual_review` \| `retry` |
| evidence_summary | object | Operator-facing short map |

## TargetEvaluation

| Field | Type | Notes |
|-------|------|-------|
| target_id | string | |
| status | enum | `passed` \| `failed` \| `skipped` \| `deferred` |
| detail | string \| null | Human-readable |
| `deferred` | — | Used for `document_field` (OCR elsewhere) |

## Validation rules (cross-cutting)

1. Reject job if any `media.uri` missing on disk when kind requires local file.
2. Reject unknown `enabled_plugins` names at validation time.
3. `spoof_score` / `replay_score` default to neutral (e.g. 0.0) if plugin
   skipped—policy interprets missing plugins via reason `PLUGIN_SKIPPED`.
4. Monotonicity: video layer does not mutate session status; caller does.

## State transitions (session, caller-owned)

Relevant fragment when video jobs run:

`FACE_DETECTED` / `CHALLENGE_RUNNING` → (job completes) → evidence attached →
retry within challenge OR advance plan.

Retries only inside challenge states (constitution).
