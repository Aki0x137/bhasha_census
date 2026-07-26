"""Field normalization and name/DOB consistency checker."""
from __future__ import annotations

import re
import uuid
import time

from shared.schemas.common import ReasonCode
from shared.schemas.document_evidence import DocumentEvidence
from shared.utils.logging import get_logger

logger = get_logger(__name__)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def _name_match(extracted: str, claimed: str) -> float:
    e = set(_normalize(extracted).split())
    c = set(_normalize(claimed).split())
    if not c:
        return 0.0
    overlap = e & c
    return len(overlap) / len(c)


def _dob_match(extracted: str, claimed: str) -> float:
    e = re.sub(r"[^0-9]", "", extracted)
    c = re.sub(r"[^0-9]", "", claimed)
    if not c or not e:
        return 0.0
    if e == c:
        return 1.0
    if len(c) >= 4 and c[:4] in e:
        return 0.7
    return 0.0


def build_document_evidence(
    session_id: str,
    digitize_result: dict,
    census_name: str | None,
    census_dob: str | None,
    image_path: str,
) -> DocumentEvidence:
    text = digitize_result.get("document_text", "")
    fields = digitize_result.get("structured_output", {})
    quality = digitize_result.get("quality_score", 0.0)

    reason_codes: list[str] = []
    match_scores: list[float] = []

    if not text.strip():
        reason_codes.append(ReasonCode.DOC_UNREADABLE.value)
        return DocumentEvidence(
            evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            timestamp_ms=int(time.time() * 1000),
            document_quality_score=quality,
            document_match_score=0.0,
            reason_codes=reason_codes,
            payload_ref=image_path,
        )

    reason_codes.append(ReasonCode.DOC_READABLE.value)

    if census_name:
        extracted_name = fields.get("full_name", text)
        score = _name_match(str(extracted_name), census_name)
        match_scores.append(score)
        if score >= 0.6:
            reason_codes.append(ReasonCode.DOC_MATCH_OK.value)
        else:
            reason_codes.append(ReasonCode.DOC_MISMATCH.value)

    if census_dob:
        extracted_dob = str(fields.get("date_of_birth", ""))
        score = _dob_match(extracted_dob, census_dob)
        match_scores.append(score)

    overall_match = (sum(match_scores) / len(match_scores)) if match_scores else 0.5

    return DocumentEvidence(
        evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        timestamp_ms=int(time.time() * 1000),
        document_text=text,
        detected_fields=fields,
        document_quality_score=quality,
        document_match_score=round(overall_match, 3),
        reason_codes=reason_codes,
        payload_ref=image_path,
    )
