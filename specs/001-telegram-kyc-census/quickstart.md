# Quickstart: Pluggable Video Verification Layer

**Feature**: `001-telegram-kyc-census`  
**OS**: Linux or macOS  
**Goal**: Run the video pipeline locally against a sample image with
challenge params and document-field verification targets.

## Prerequisites

- Python 3.11+
- pip
- (Optional) Temporal CLI/server for activity mode
- Sample face photo under `evidence/demo/`

## 1. Install

```bash
cd /path/to/bhasaha_census
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-video.txt   # created during implementation
# or: pip install pydantic opencv-python-headless mediapipe numpy temporalio fastapi uvicorn pytest
```

## 2. Layout to create during implementation

```text
shared/schemas/verification_job.py
shared/schemas/video_evidence.py
services/video/pipeline.py
services/video/registry.py
services/video/plugins/
services/video/activity.py
apps/api/  # POST /video/verify
```

## 3. Smoke test with fixture job

Save as `evidence/demo/job.json` (adjust `uri`):

```json
{
  "job_id": "job_demo_1",
  "session_id": "sess_demo",
  "created_at_ms": 1721980000000,
  "media": [
    {
      "media_id": "m1",
      "uri": "evidence/demo/face.jpg",
      "kind": "photo"
    }
  ],
  "params": {
    "challenge_id": "c1",
    "challenge_type": "LOOK_LEFT_RIGHT",
    "prompt_text": "Look left then right",
    "expected_response": "look_left_right",
    "time_limit_ms": 15000,
    "min_confidence": 0.7,
    "max_attempts": 2,
    "seed": 42
  },
  "targets": [
    {
      "target_id": "t_face",
      "kind": "presence",
      "required": true,
      "weight": 1.0
    },
    {
      "target_id": "t_dob",
      "kind": "document_field",
      "field_name": "date_of_birth",
      "expected_value": "1990-01-01",
      "required": true,
      "weight": 1.0,
      "metadata": { "compare_in": "document_service" }
    }
  ]
}
```

### CLI / module (target UX after implement)

```bash
python -m services.video.pipeline --job evidence/demo/job.json
```

Expect stdout JSON `VideoEvidence` with `targets_evaluation` marking
`t_dob` as `deferred` and face presence passed/failed from plugins.

### HTTP demo

```bash
uvicorn apps.api.main:app --reload --port 8000
curl -s localhost:8000/video/plugins | jq .
curl -s -X POST localhost:8000/video/verify \
  -H 'content-type: application/json' \
  -d @evidence/demo/job.json | jq .
```

## 4. Temporal worker (optional)

```bash
# start local Temporal (dev)
# then:
python -m services.video.worker
```

Enrollment workflows call activity `analyze_verification_job` with the same
schema.

## 5. Privacy notes

- Keep demo media under `evidence/` (gitignored in real use).
- Do not commit real ID photos.
- Prefer deleting raw clips after debug; retain scores + `payload_ref` only
  when needed for review.

## 6. Acceptance check (this slice)

- [ ] Unknown plugin names → 422 / validation error
- [ ] Missing media file → clear error
- [ ] `document_field` targets → `deferred` in `targets_evaluation`
- [ ] Face-less image → `hard_fail_hint` true and `FACE_MISSING` reason
- [ ] Multi-face image → `MULTI_FACE` / user-visible retry or fail (not silent)
- [ ] Unit tests for schema + fake plugin registry pass on Linux and macOS

## 7. Demo timing notes (spec success criteria — manual)

Not CI gates; record during a scripted demo:

- [ ] SC-001: Consent + census Q&A completes in under 5 minutes
- [ ] SC-005: Happy-path E2E (questions + challenges + document + verdict)
      completes in under 15 minutes
- [ ] SC-002 / SC-003: Spot-check presence/speech completion and readable
      document extraction on the demo fixture set
