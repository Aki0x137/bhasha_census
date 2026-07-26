"""Finalize enrollment: aggregate evidence → policy verdict → Bedrock explanation."""
from __future__ import annotations

import time

from apps.api.db.session_store import get_session
from shared.schemas.common import SessionStatus
from shared.schemas.decision import EnrollmentDecision
from shared.schemas.evidence_bundle import EvidenceBundle
from shared.schemas.session import EnrollmentSession
from shared.utils.logging import get_logger

from services.policy.verdict import run_policy
from services.orchestrator.verdict_explainer import explain_verdict

logger = get_logger(__name__)


async def finalize_enrollment(session: EnrollmentSession) -> EnrollmentDecision:
    """
    Gather evidence from DB, run deterministic policy, attach Bedrock explanation.
    """
    bundle = _build_bundle(session)
    decision = run_policy(bundle)
    explanation = explain_verdict(decision, bundle)

    # Attach human-readable explanation to evidence_summary
    decision.evidence_summary["explanation"] = explanation.get("summary", "")
    decision.evidence_summary["explanation_reasons"] = explanation.get("reasons", [])

    logger.info(
        "enrollment_finalized",
        session_id=session.session_id,
        verdict=decision.verdict.value,
        confidence=decision.confidence,
    )
    return decision


def _build_bundle(session: EnrollmentSession) -> EvidenceBundle:
    """Reconstruct EvidenceBundle from persisted evidence ids on the session."""
    # For MVP, evidence objects aren't separately stored in DB;
    # we load them from the session's challenge outcomes.
    from shared.schemas.video_evidence import VideoEvidence, VideoEvidenceScores
    from shared.schemas.speech_evidence import SpeechEvidence
    from shared.schemas.document_evidence import DocumentEvidence

    video: list[VideoEvidence] = []
    speech: list[SpeechEvidence] = []
    document: list[DocumentEvidence] = []

    for item in session.challenge_plan:
        if not item.completed:
            continue
        if item.challenge_type in ("LOOK_LEFT_RIGHT", "BLINK_TWICE", "SMILE_AND_TILT"):
            passed = item.outcome == "passed"
            video.append(VideoEvidence(
                evidence_id=f"syn_{item.challenge_id}",
                job_id=f"syn_{item.challenge_id}",
                session_id=session.session_id,
                timestamp_ms=int(time.time() * 1000),
                scores=VideoEvidenceScores(
                    face_present=passed,
                    face_count=1 if passed else 0,
                    quality_score=0.7 if passed else 0.2,
                    spoof_score=0.1 if passed else 0.5,
                ),
                reason_codes=["FACE_PRESENT", "QUALITY_OK"] if passed else ["FACE_MISSING"],
            ))
        elif item.challenge_type == "SAY_RANDOM_PHRASE":
            passed = item.outcome == "passed"
            speech.append(SpeechEvidence(
                evidence_id=f"syn_{item.challenge_id}_speech",
                session_id=session.session_id,
                challenge_id=item.challenge_id,
                timestamp_ms=int(time.time() * 1000),
                phrase_match_score=0.9 if passed else 0.2,
                keyword_match_score=0.9 if passed else 0.2,
                reason_codes=["SPEECH_MATCH_OK"] if passed else ["SPEECH_MISMATCH"],
            ))
        elif item.challenge_type == "SHOW_ID_AND_READ_FIELD":
            passed = item.outcome == "passed"
            document.append(DocumentEvidence(
                evidence_id=f"syn_{item.challenge_id}_doc",
                session_id=session.session_id,
                timestamp_ms=int(time.time() * 1000),
                document_quality_score=0.8 if passed else 0.3,
                document_match_score=0.8 if passed else 0.3,
                reason_codes=["DOC_READABLE", "DOC_MATCH_OK"] if passed else ["DOC_UNREADABLE"],
            ))

    return EvidenceBundle(
        session_id=session.session_id,
        video=video,
        speech=speech,
        document=document,
        collected_at_ms=int(time.time() * 1000),
    )
