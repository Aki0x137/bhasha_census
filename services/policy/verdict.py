"""Deterministic policy fusion — weights, thresholds, hard-fails.

LLM is NOT the sole authority here (constitution Principle V).
EvidenceBundle feeds this function; it returns EnrollmentDecision.
"""
from __future__ import annotations

from shared.schemas.common import EnrollmentVerdict, NextAction, ReasonCode
from shared.schemas.decision import EnrollmentDecision
from shared.schemas.evidence_bundle import EvidenceBundle
from shared.utils.logging import get_logger

logger = get_logger(__name__)

# ── thresholds ──────────────────────────────────────────────────────────────
_VIDEO_PRESENCE_REQUIRED = True   # at least 1 VideoEvidence with face_present
_SPOOF_HARD_FAIL = 0.85           # reject if any video evidence spoof_score ≥ this
_VIDEO_MIN_QUALITY = 0.35
_SPEECH_PASS_SCORE = 0.55
_DOC_MATCH_PASS = 0.60
_DOC_QUALITY_MIN = 0.40

# ── weights for composite score ─────────────────────────────────────────────
_W_VIDEO = 0.40
_W_SPEECH = 0.30
_W_DOC = 0.30


def run_policy(bundle: EvidenceBundle) -> EnrollmentDecision:
    reason_codes: list[str] = []
    hard_fail = False
    scores: dict[str, float] = {}

    # ── VIDEO ────────────────────────────────────────────────────────────────
    video_score = 0.0
    if bundle.video:
        spoof_max = max(e.scores.spoof_score for e in bundle.video)
        if spoof_max >= _SPOOF_HARD_FAIL:
            hard_fail = True
            reason_codes.append(ReasonCode.SPOOF_SUSPECT.value)

        face_present_any = any(e.scores.face_present for e in bundle.video)
        if not face_present_any:
            hard_fail = True
            reason_codes.append(ReasonCode.FACE_MISSING.value)

        multi_face_any = any(ReasonCode.MULTI_FACE.value in e.reason_codes for e in bundle.video)
        if multi_face_any:
            reason_codes.append(ReasonCode.MULTI_FACE.value)
            hard_fail = True

        avg_quality = sum(e.scores.quality_score for e in bundle.video) / len(bundle.video)
        if avg_quality < _VIDEO_MIN_QUALITY:
            reason_codes.append(ReasonCode.QUALITY_LOW.value)

        # Video score = avg of quality + (1 - spoof) + face_present indicator
        video_score = min(
            (avg_quality + max(0.0, 1.0 - spoof_max) + (1.0 if face_present_any else 0.0)) / 3.0,
            1.0,
        )
        scores["video"] = round(video_score, 3)
    else:
        reason_codes.append("NO_VIDEO_EVIDENCE")

    # ── SPEECH ───────────────────────────────────────────────────────────────
    speech_score = 0.0
    if bundle.speech:
        speech_score = max(e.phrase_match_score for e in bundle.speech)
        scores["speech"] = round(speech_score, 3)
        if speech_score < _SPEECH_PASS_SCORE:
            reason_codes.append(ReasonCode.SPEECH_MISMATCH.value)
        else:
            reason_codes.append(ReasonCode.SPEECH_MATCH_OK.value)
    else:
        reason_codes.append("NO_SPEECH_EVIDENCE")

    # ── DOCUMENT ─────────────────────────────────────────────────────────────
    doc_score = 0.0
    if bundle.document:
        best = max(bundle.document, key=lambda e: e.document_match_score)
        doc_score = best.document_match_score
        scores["document"] = round(doc_score, 3)
        if best.document_quality_score < _DOC_QUALITY_MIN:
            reason_codes.append(ReasonCode.DOC_UNREADABLE.value)
        elif doc_score >= _DOC_MATCH_PASS:
            reason_codes.append(ReasonCode.DOC_MATCH_OK.value)
        else:
            reason_codes.append(ReasonCode.DOC_MISMATCH.value)
    else:
        reason_codes.append("NO_DOC_EVIDENCE")

    # ── COMPOSITE ────────────────────────────────────────────────────────────
    composite = _W_VIDEO * video_score + _W_SPEECH * speech_score + _W_DOC * doc_score
    scores["composite"] = round(composite, 3)

    if hard_fail:
        verdict = EnrollmentVerdict.REJECTED
        next_action = NextAction.MANUAL_REVIEW
    elif composite >= 0.70:
        verdict = EnrollmentVerdict.APPROVED
        next_action = NextAction.ALLOW
    elif composite >= 0.45:
        verdict = EnrollmentVerdict.NEEDS_REVIEW
        next_action = NextAction.MANUAL_REVIEW
    elif not bundle.video or not bundle.speech:
        verdict = EnrollmentVerdict.NEEDS_MORE_EVIDENCE
        next_action = NextAction.RETRY
    else:
        verdict = EnrollmentVerdict.REJECTED
        next_action = NextAction.MANUAL_REVIEW

    logger.info(
        "policy_verdict",
        session_id=bundle.session_id,
        verdict=verdict.value,
        composite=composite,
        hard_fail=hard_fail,
    )
    return EnrollmentDecision(
        session_id=bundle.session_id,
        verdict=verdict,
        confidence=round(composite, 3),
        reason_codes=reason_codes,
        next_action=next_action,
        evidence_summary=scores,
    )
