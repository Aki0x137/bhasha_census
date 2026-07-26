"""EnrollmentSession and CensusProfile typed models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from shared.schemas.common import SessionStatus


class CensusProfile(BaseModel):
    full_name: str | None = None
    dob_or_age: str | None = None
    gender: str | None = None
    locality: str | None = None
    household_size: int | None = None


class ChallengePlanItem(BaseModel):
    challenge_id: str
    challenge_type: str
    completed: bool = False
    outcome: str | None = None


class EnrollmentSession(BaseModel):
    session_id: str
    user_ref: str
    status: SessionStatus = SessionStatus.CREATED
    consent_accepted: bool = False
    census_profile: CensusProfile = Field(default_factory=CensusProfile)
    challenge_plan: list[ChallengePlanItem] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    final_verdict: str | None = None
    locale: str = "en-IN"
    created_at_ms: int = 0
    updated_at_ms: int = 0
    expires_at_ms: int = 0
