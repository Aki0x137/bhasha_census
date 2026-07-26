"""Challenge engine — deterministic challenge params from a plan item + seed."""
from __future__ import annotations

import random
import time

from shared.schemas.common import ChallengeType
from shared.schemas.verification_job import ChallengeParams

_PHRASES = [
    "the sky is blue today",
    "census enrollment is open",
    "verify my identity now",
    "open sesame welcome home",
    "bhasaha census portal",
]

_POSE_LABELS = {
    ChallengeType.LOOK_LEFT_RIGHT: "look left then right",
    ChallengeType.BLINK_TWICE: "blink twice",
    ChallengeType.SMILE_AND_TILT: "smile and tilt your head",
}


def build_challenge_params(
    challenge_id: str,
    challenge_type: ChallengeType,
    seed: int | None = None,
) -> ChallengeParams:
    rng = random.Random(seed or hash(challenge_id))

    if challenge_type == ChallengeType.SAY_RANDOM_PHRASE:
        phrase = rng.choice(_PHRASES)
        return ChallengeParams(
            challenge_id=challenge_id,
            challenge_type=challenge_type,
            prompt_text=f"Say: '{phrase}'",
            expected_response=phrase,
            time_limit_ms=15000,
            min_confidence=0.6,
            max_attempts=2,
            seed=seed,
            enabled_plugins=["face_detector", "frame_quality", "mouth_movement_detector"],
        )
    elif challenge_type == ChallengeType.SHOW_ID_AND_READ_FIELD:
        return ChallengeParams(
            challenge_id=challenge_id,
            challenge_type=challenge_type,
            prompt_text="Please show your identity document clearly to the camera",
            expected_response=None,
            time_limit_ms=20000,
            min_confidence=0.6,
            max_attempts=2,
            seed=seed,
            enabled_plugins=["face_detector", "frame_quality", "doc_frame_cue"],
        )
    else:
        label = _POSE_LABELS.get(challenge_type, "follow the instruction")
        return ChallengeParams(
            challenge_id=challenge_id,
            challenge_type=challenge_type,
            prompt_text=label.capitalize(),
            expected_response=challenge_type.value.lower(),
            time_limit_ms=15000,
            min_confidence=0.65,
            max_attempts=2,
            seed=seed,
            enabled_plugins=[
                "face_detector",
                "frame_quality",
                "pose_estimator",
                "spoof_detector",
            ],
        )
