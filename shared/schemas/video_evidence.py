"""VideoEvidence — typed output from the pluggable video pipeline."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from shared.schemas.common import TargetStatus


class PluginResult(BaseModel):
    plugin_name: str
    plugin_version: str
    ok: bool
    scores: dict[str, Any] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    error_message: str | None = None
    duration_ms: int = 0


class VideoEvidenceScores(BaseModel):
    face_present: bool = False
    face_count: int = 0
    track_stable: bool = False
    quality_score: float = 0.0
    motion_score: float = 0.0
    spoof_score: float = 0.0
    replay_score: float = 0.0
    doc_visible_score: float | None = None
    pose_match_score: float | None = None
    hard_fail_hint: bool = False


class TargetEvaluation(BaseModel):
    target_id: str
    status: TargetStatus
    detail: str | None = None


class VideoEvidence(BaseModel):
    evidence_id: str
    job_id: str
    session_id: str
    type: str = "video"
    timestamp_ms: int
    source: str = "worker"
    payload_ref: str | None = None
    scores: VideoEvidenceScores = Field(default_factory=VideoEvidenceScores)
    reason_codes: list[str] = Field(default_factory=list)
    plugin_results: list[PluginResult] = Field(default_factory=list)
    targets_evaluation: list[TargetEvaluation] = Field(default_factory=list)
