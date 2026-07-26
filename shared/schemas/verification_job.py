"""VerificationJob — typed input for the pluggable video layer."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from shared.schemas.common import ChallengeType, MediaKind, TargetKind


class MediaRef(BaseModel):
    media_id: str
    uri: str
    kind: MediaKind
    captured_at_ms: int | None = None
    content_type: str | None = None


class ChallengeParams(BaseModel):
    challenge_id: str
    challenge_type: ChallengeType
    prompt_text: str
    expected_response: str | None = None
    time_limit_ms: int = Field(..., gt=0)
    min_confidence: float = Field(..., ge=0.0, le=1.0)
    max_attempts: int = Field(..., ge=1)
    seed: int | None = None
    quality_min: float | None = Field(default=None, ge=0.0, le=1.0)
    spoof_max: float | None = Field(default=None, ge=0.0, le=1.0)
    enabled_plugins: list[str] | None = None


class VerificationTarget(BaseModel):
    target_id: str
    kind: TargetKind
    field_name: str | None = None
    expected_value: str | None = None
    required: bool = True
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def _check_depth(cls, v: dict[str, Any]) -> dict[str, Any]:
        for val in v.values():
            if isinstance(val, dict):
                for inner in val.values():
                    if isinstance(inner, dict):
                        raise ValueError("metadata max depth is 2")
        return v


class VerificationJob(BaseModel):
    job_id: str
    session_id: str
    locale: str = "en-IN"
    created_at_ms: int = Field(..., ge=0)
    media: list[MediaRef] = Field(..., min_length=1)
    params: ChallengeParams
    targets: list[VerificationTarget] = Field(default_factory=list)
