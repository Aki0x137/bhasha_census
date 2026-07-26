# Contract: VerificationJob (video layer input)

**Package target**: `shared/schemas/verification_job.py` (Pydantic v2)  
**Transport**: Temporal activity payload JSON / FastAPI JSON body

## Purpose

Single typed input for the pluggable video layer: media + challenge params +
verification targets (including document field claims to verify in-process
via sibling services).

## JSON Schema (draft 2020-12 style)

```json
{
  "$id": "https://bhasaha.local/schemas/verification-job.json",
  "title": "VerificationJob",
  "type": "object",
  "additionalProperties": false,
  "required": ["job_id", "session_id", "media", "params", "created_at_ms"],
  "properties": {
    "job_id": { "type": "string", "minLength": 1 },
    "session_id": { "type": "string", "minLength": 1 },
    "locale": { "type": "string", "default": "en-IN" },
    "created_at_ms": { "type": "integer", "minimum": 0 },
    "media": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/MediaRef" }
    },
    "params": { "$ref": "#/$defs/ChallengeParams" },
    "targets": {
      "type": "array",
      "default": [],
      "items": { "$ref": "#/$defs/VerificationTarget" }
    }
  },
  "$defs": {
    "MediaRef": {
      "type": "object",
      "additionalProperties": false,
      "required": ["media_id", "uri", "kind"],
      "properties": {
        "media_id": { "type": "string" },
        "uri": { "type": "string" },
        "kind": { "enum": ["photo", "video_clip", "frame_sequence"] },
        "captured_at_ms": { "type": ["integer", "null"] },
        "content_type": { "type": ["string", "null"] }
      }
    },
    "ChallengeParams": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "challenge_id",
        "challenge_type",
        "prompt_text",
        "time_limit_ms",
        "min_confidence",
        "max_attempts"
      ],
      "properties": {
        "challenge_id": { "type": "string" },
        "challenge_type": {
          "enum": [
            "LOOK_LEFT_RIGHT",
            "BLINK_TWICE",
            "SMILE_AND_TILT",
            "SAY_RANDOM_PHRASE",
            "SHOW_ID_AND_READ_FIELD",
            "CUSTOM"
          ]
        },
        "prompt_text": { "type": "string" },
        "expected_response": { "type": ["string", "null"] },
        "time_limit_ms": { "type": "integer", "minimum": 1 },
        "min_confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "max_attempts": { "type": "integer", "minimum": 1 },
        "seed": { "type": ["integer", "null"] },
        "quality_min": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "spoof_max": { "type": ["number", "null"], "minimum": 0, "maximum": 1 },
        "enabled_plugins": {
          "type": ["array", "null"],
          "items": { "type": "string" }
        }
      }
    },
    "VerificationTarget": {
      "type": "object",
      "additionalProperties": false,
      "required": ["target_id", "kind", "required"],
      "properties": {
        "target_id": { "type": "string" },
        "kind": {
          "enum": [
            "presence",
            "pose",
            "liveness_cue",
            "document_field",
            "document_visible",
            "anti_spoof"
          ]
        },
        "field_name": { "type": ["string", "null"] },
        "expected_value": { "type": ["string", "null"] },
        "required": { "type": "boolean" },
        "weight": { "type": "number", "minimum": 0, "maximum": 1, "default": 1 },
        "metadata": { "type": "object" }
      }
    }
  }
}
```

## Example

```json
{
  "job_id": "job_01HZX",
  "session_id": "sess_123",
  "locale": "en-IN",
  "created_at_ms": 1721980000000,
  "media": [
    {
      "media_id": "m1",
      "uri": "evidence/sess_123/video/challenge1.jpg",
      "kind": "photo",
      "content_type": "image/jpeg"
    }
  ],
  "params": {
    "challenge_id": "c1",
    "challenge_type": "LOOK_LEFT_RIGHT",
    "prompt_text": "Look left, then right",
    "expected_response": "look_left_right",
    "time_limit_ms": 15000,
    "min_confidence": 0.7,
    "max_attempts": 2,
    "seed": 42,
    "enabled_plugins": [
      "face_detector",
      "frame_quality",
      "pose_estimator",
      "spoof_detector"
    ]
  },
  "targets": [
    {
      "target_id": "t_face",
      "kind": "presence",
      "required": true,
      "weight": 1.0,
      "field_name": null,
      "expected_value": null,
      "metadata": {}
    },
    {
      "target_id": "t_name",
      "kind": "document_field",
      "field_name": "full_name",
      "expected_value": "Asha Kumar",
      "required": true,
      "weight": 1.0,
      "metadata": { "compare_in": "document_service" }
    }
  ]
}
```
