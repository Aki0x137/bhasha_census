"""Enrollment verdict payload."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel
from shared.schemas.common import EnrollmentVerdict, NextAction


class EnrollmentDecision(BaseModel):
    session_id: str
    verdict: EnrollmentVerdict
    confidence: float = 0.0
    reason_codes: list[str]
    next_action: NextAction
    evidence_summary: dict[str, Any]
