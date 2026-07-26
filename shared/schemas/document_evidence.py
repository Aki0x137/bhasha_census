"""DocumentEvidence — typed output from document digitization and field matching."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class DocumentEvidence(BaseModel):
    evidence_id: str
    session_id: str
    type: str = "document"
    timestamp_ms: int
    document_text: str | None = None
    detected_fields: dict[str, Any] = Field(default_factory=dict)
    document_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    document_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    payload_ref: str | None = None
