"""EvidenceBundle — aggregates all evidence branches for policy fusion (FR-009)."""
from __future__ import annotations

from pydantic import BaseModel, Field
from shared.schemas.video_evidence import VideoEvidence
from shared.schemas.speech_evidence import SpeechEvidence
from shared.schemas.document_evidence import DocumentEvidence


class EvidenceBundle(BaseModel):
    session_id: str
    video: list[VideoEvidence] = Field(default_factory=list)
    speech: list[SpeechEvidence] = Field(default_factory=list)
    document: list[DocumentEvidence] = Field(default_factory=list)
    collected_at_ms: int = 0
