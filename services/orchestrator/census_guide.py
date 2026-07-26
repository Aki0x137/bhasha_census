"""Census conversation guide.

For US1 demo, uses deterministic scripted responses (no hallucination).
LangGraph/Bedrock patterns land in US4 explainer — see services/orchestrator/finalize.py.
FR-004: guide MUST NOT invent personal facts the resident did not provide.
"""
from __future__ import annotations

from shared.schemas.session import CensusProfile
from apps.telegram.i18n.messages import get_message


def build_confirmation_text(profile: CensusProfile, locale: str = "en") -> str:
    """Render a summary of the census profile for user confirmation."""
    return get_message(
        "confirm_profile",
        locale=locale,
        full_name=profile.full_name or "—",
        dob_or_age=profile.dob_or_age or "—",
        gender=profile.gender or "—",
        locality=profile.locality or "—",
        household_size=str(profile.household_size) if profile.household_size is not None else "—",
    )


def clarify_answer(field: str, raw: str, locale: str = "en") -> str | None:
    """Return a follow-up clarification if the answer looks incomplete.

    Only re-states or prompts — never invents a value.
    """
    raw = raw.strip()
    if not raw:
        questions = {
            "full_name": get_message("ask_name", locale),
            "dob_or_age": get_message("ask_dob", locale),
            "gender": get_message("ask_gender", locale),
            "locality": get_message("ask_locality", locale),
            "household_size": get_message("ask_household", locale),
        }
        return questions.get(field)
    return None
