"""Build a VerificationJob from a challenge plan item + census claim targets."""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from shared.schemas.common import ChallengeType, TargetKind
from shared.schemas.session import EnrollmentSession
from shared.schemas.verification_job import MediaRef, MediaKind, VerificationJob, VerificationTarget
from services.policy.challenge_engine import build_challenge_params


def build_video_job(
    session: EnrollmentSession,
    challenge_id: str,
    challenge_type: ChallengeType,
    media_path: str | Path,
    media_kind: MediaKind = MediaKind.PHOTO,
) -> VerificationJob:
    params = build_challenge_params(challenge_id, challenge_type)
    targets: list[VerificationTarget] = [
        VerificationTarget(target_id=f"{challenge_id}_presence", kind=TargetKind.PRESENCE, required=True)
    ]

    if challenge_type == ChallengeType.SHOW_ID_AND_READ_FIELD:
        targets.append(
            VerificationTarget(
                target_id=f"{challenge_id}_doc_visible",
                kind=TargetKind.DOCUMENT_VISIBLE,
                required=False,
            )
        )
        profile = session.census_profile
        if profile.full_name:
            targets.append(
                VerificationTarget(
                    target_id=f"{challenge_id}_name",
                    kind=TargetKind.DOCUMENT_FIELD,
                    field_name="full_name",
                    expected_value=profile.full_name,
                    required=True,
                    metadata={"compare_in": "document_service"},
                )
            )
        if profile.dob_or_age:
            targets.append(
                VerificationTarget(
                    target_id=f"{challenge_id}_dob",
                    kind=TargetKind.DOCUMENT_FIELD,
                    field_name="date_of_birth",
                    expected_value=profile.dob_or_age,
                    required=True,
                    metadata={"compare_in": "document_service"},
                )
            )

    return VerificationJob(
        job_id=f"job_{uuid.uuid4().hex[:10]}",
        session_id=session.session_id,
        locale=session.locale,
        created_at_ms=int(time.time() * 1000),
        media=[
            MediaRef(
                media_id=f"m_{uuid.uuid4().hex[:8]}",
                uri=str(media_path),
                kind=media_kind,
            )
        ],
        params=params,
        targets=targets,
    )
