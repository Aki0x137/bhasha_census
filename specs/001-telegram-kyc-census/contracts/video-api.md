# Contract: Video verify HTTP API (local demo)

**Service**: `apps/api` (FastAPI)  
**Auth**: none for local MVP (bind localhost only)

## `POST /video/verify`

Runs the pluggable video pipeline synchronously (or enqueues Temporal
activity when worker mode is enabled via config).

### Request

Body: `VerificationJob` — see [verification-job.md](./verification-job.md)

### Responses

| Status | Body | When |
|--------|------|------|
| 200 | `VideoEvidence` | Success |
| 422 | validation error | Schema/plugin name invalid |
| 404 | `{ "detail": "media not found" }` | `uri` missing on disk |
| 500 | `{ "detail": "pipeline_error", "job_id": "..." }` | Unexpected plugin crash after retries |

## `GET /video/plugins`

Lists registered plugins for operator/debug.

### Response 200

```json
{
  "plugins": [
    {
      "name": "face_detector",
      "version": "0.1.0",
      "capabilities": ["face"]
    }
  ]
}
```

## Temporal activity

- **Name**: `analyze_verification_job`
- **Input**: `VerificationJob`
- **Output**: `VideoEvidence`
- **Retry**: once on transient IO; do not retry deterministic validation errors
