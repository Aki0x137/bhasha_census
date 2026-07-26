"""SpeechEvidence — typed boundary for speech challenge results (constitution Principle III)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SpeechEvidence(BaseModel):
    evidence_id: str
    session_id: str
    challenge_id: str
    type: str = "speech"
    timestamp_ms: int
    transcript: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: int = 0
    keyword_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    phrase_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    payload_ref: str | None = None
