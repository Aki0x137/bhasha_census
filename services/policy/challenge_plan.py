"""Challenge plan stub generator (US1 — deferred challenges seeded for later stories)."""
from __future__ import annotations

import random

from shared.schemas.common import ChallengeType
from shared.schemas.session import ChallengePlanItem

_PHYSICAL_CHALLENGES = [
    ChallengeType.LOOK_LEFT_RIGHT,
    ChallengeType.BLINK_TWICE,
    ChallengeType.SMILE_AND_TILT,
]

_SPEECH_PHRASES = [
    "the sky is blue",
    "census enrollment today",
    "my name is verified",
    "open sesame please",
]


def generate_challenge_plan(session_id: str, seed: int | None = None) -> list[ChallengePlanItem]:
    """Generate a minimal MVP challenge plan for a session."""
    rng = random.Random(seed or hash(session_id))
    physical = rng.choice(_PHYSICAL_CHALLENGES)
    phrase = rng.choice(_SPEECH_PHRASES)
    return [
        ChallengePlanItem(
            challenge_id=f"{session_id}_c1",
            challenge_type=physical.value,
        ),
        ChallengePlanItem(
            challenge_id=f"{session_id}_c2",
            challenge_type=ChallengeType.SAY_RANDOM_PHRASE.value,
        ),
        ChallengePlanItem(
            challenge_id=f"{session_id}_c3",
            challenge_type=ChallengeType.SHOW_ID_AND_READ_FIELD.value,
        ),
    ]
