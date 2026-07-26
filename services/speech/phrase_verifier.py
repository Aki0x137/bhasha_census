"""Speech phrase match + latency scoring returning typed SpeechEvidence."""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from shared.schemas.speech_evidence import SpeechEvidence
from shared.schemas.common import ReasonCode
from services.speech.sarvam_stt import get_stt_client
from shared.utils.logging import get_logger

logger = get_logger(__name__)

_LATENCY_OK_MS = 5000  # under 5s = ok


def _keyword_score(transcript: str, expected: str) -> float:
    if not expected:
        return 0.5
    t_words = set(transcript.lower().split())
    e_words = set(expected.lower().split())
    if not e_words:
        return 0.5
    overlap = t_words & e_words
    return len(overlap) / len(e_words)


def _phrase_score(transcript: str, expected: str) -> float:
    if not expected:
        return 0.5
    t = transcript.lower().strip()
    e = expected.lower().strip()
    if t == e:
        return 1.0
    # Partial: ratio of longest common subsequence
    common = sum(1 for c in e if c in t)
    return common / max(len(e), 1)


def verify_phrase(
    audio_path: str | Path,
    session_id: str,
    challenge_id: str,
    expected_phrase: str,
    locale: str = "en-IN",
) -> SpeechEvidence:
    client = get_stt_client()
    t0 = time.monotonic()
    result = client.transcribe(str(audio_path), language_code=locale)
    latency_ms = result["latency_ms"]
    transcript = result["transcript"]
    confidence = result["confidence"]

    kw_score = _keyword_score(transcript, expected_phrase)
    ph_score = _phrase_score(transcript, expected_phrase)

    reason_codes: list[str] = []
    reason_codes.append(
        ReasonCode.SPEECH_MATCH_OK.value if ph_score >= 0.6 else ReasonCode.SPEECH_MISMATCH.value
    )
    reason_codes.append(
        ReasonCode.SPEECH_LATENCY_OK.value
        if latency_ms <= _LATENCY_OK_MS
        else ReasonCode.SPEECH_LATENCY_HIGH.value
    )

    evidence = SpeechEvidence(
        evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        challenge_id=challenge_id,
        timestamp_ms=int(time.time() * 1000),
        transcript=transcript,
        confidence=confidence,
        latency_ms=latency_ms,
        keyword_match_score=round(kw_score, 3),
        phrase_match_score=round(ph_score, 3),
        reason_codes=reason_codes,
        payload_ref=str(audio_path),
    )
    logger.info(
        "speech_verified",
        session_id=session_id,
        challenge_id=challenge_id,
        phrase_score=ph_score,
        latency_ms=latency_ms,
    )
    return evidence
