"""Session routes: POST /sessions/{id}/finalize, GET /sessions/{id}."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.db.session_store import get_session, update_session
from shared.schemas.common import SessionStatus
from shared.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}")
def get_session_summary(session_id: str) -> dict:
    sess = get_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": sess.session_id,
        "status": sess.status.value,
        "census_profile": sess.census_profile.model_dump(exclude_none=True),
        "evidence_ids": sess.evidence_ids,
        "final_verdict": sess.final_verdict,
        "challenge_plan": [c.model_dump() for c in sess.challenge_plan],
    }


@router.post("/{session_id}/finalize")
async def finalize_session(session_id: str) -> dict:
    sess = get_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    from services.orchestrator.finalize import finalize_enrollment
    decision = await finalize_enrollment(sess)
    sess.final_verdict = decision.verdict.value
    sess.status = SessionStatus.COMPLETED
    update_session(sess)
    logger.info("session_finalized", session_id=session_id, verdict=decision.verdict.value)
    return decision.model_dump()
