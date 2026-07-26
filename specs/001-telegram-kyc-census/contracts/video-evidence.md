# Contract: VideoEvidence (video layer output)

**Package target**: `shared/schemas/video_evidence.py` (Pydantic v2)  
**Transport**: Temporal activity return JSON / FastAPI response body

## Purpose

Typed evidence from the pluggable video pipeline for policy fusion and
operator review. Includes per-target evaluation for params/docs declared on
the job (`document_field` → `deferred` until document service runs).

## JSON Schema

```json
{
  "$id": "https://bhasaha.local/schemas/video-evidence.json",
  "title": "VideoEvidence",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "evidence_id",
    "job_id",
    "session_id",
    "type",
    "timestamp_ms",
    "source",
    "scores",
    "reason_codes",
    "plugin_results",
    "targets_evaluation"
  ],
  "properties": {
    "evidence_id": { "type": "string" },
    "job_id": { "type": "string" },
    "session_id": { "type": "string" },
    "type": { "const": "video" },
    "timestamp_ms": { "type": "integer", "minimum": 0 },
    "source": { "const": "worker" },
    "payload_ref": { "type": ["string", "null"] },
    "scores": { "$ref": "#/$defs/VideoEvidenceScores" },
    "reason_codes": { "type": "array", "items": { "type": "string" } },
    "plugin_results": {
      "type": "array",
      "items": { "$ref": "#/$defs/PluginResult" }
    },
    "targets_evaluation": {
      "type": "array",
      "items": { "$ref": "#/$defs/TargetEvaluation" }
    }
  },
  "$defs": {
    "VideoEvidenceScores": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "face_present",
        "face_count",
        "track_stable",
        "quality_score",
        "motion_score",
        "spoof_score",
        "replay_score",
        "hard_fail_hint"
      ],
      "properties": {
        "face_present": { "type": "boolean" },
        "face_count": { "type": "integer", "minimum": 0 },
        "track_stable": { "type": "boolean" },
        "quality_score": { "type": "number", "minimum": 0, "maximum": 1 },
        "motion_score": { "type": "number", "minimum": 0, "maximum": 1 },
        "spoof_score": { "type": "number", "minimum": 0, "maximum": 1 },
        "replay_score": { "type": "number", "minimum": 0, "maximum": 1 },
        "doc_visible_score": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "pose_match_score": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "hard_fail_hint": { "type": "boolean" }
      }
    },
    "PluginResult": {
      "type": "object",
      "additionalProperties": false,
      "required": ["plugin_name", "plugin_version", "ok", "scores", "labels", "duration_ms"],
      "properties": {
        "plugin_name": { "type": "string" },
        "plugin_version": { "type": "string" },
        "ok": { "type": "boolean" },
        "scores": { "type": "object" },
        "labels": { "type": "array", "items": { "type": "string" } },
        "error_message": { "type": ["string", "null"] },
        "duration_ms": { "type": "integer", "minimum": 0 }
      }
    },
    "TargetEvaluation": {
      "type": "object",
      "additionalProperties": false,
      "required": ["target_id", "status"],
      "properties": {
        "target_id": { "type": "string" },
        "status": { "enum": ["passed", "failed", "skipped", "deferred"] },
        "detail": { "type": ["string", "null"] }
      }
    }
  }
}
```

## Example

```json
{
  "evidence_id": "ev_901",
  "job_id": "job_01HZX",
  "session_id": "sess_123",
  "type": "video",
  "timestamp_ms": 1721980005000,
  "source": "worker",
  "payload_ref": "evidence/sess_123/video/job_01HZX_debug.jpg",
  "scores": {
    "face_present": true,
    "face_count": 1,
    "track_stable": true,
    "quality_score": 0.88,
    "motion_score": 0.6,
    "spoof_score": 0.12,
    "replay_score": 0.05,
    "doc_visible_score": null,
    "pose_match_score": 0.81,
    "hard_fail_hint": false
  },
  "reason_codes": ["FACE_PRESENT", "CHALLENGE_POSE_OK", "QUALITY_OK"],
  "plugin_results": [
    {
      "plugin_name": "face_detector",
      "plugin_version": "0.1.0",
      "ok": true,
      "scores": { "face_count": 1 },
      "labels": ["single_face"],
      "error_message": null,
      "duration_ms": 40
    }
  ],
  "targets_evaluation": [
    { "target_id": "t_face", "status": "passed", "detail": "one face" },
    {
      "target_id": "t_name",
      "status": "deferred",
      "detail": "document_field handled by document service"
    }
  ]
}
```
