"""Census Q&A state machine — collects and confirms the minimal census profile (FR-003)."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from apps.api.db.session_store import get_session, update_session
from apps.telegram.i18n.messages import get_message
from services.orchestrator.census_guide import build_confirmation_text, clarify_answer
from services.policy.challenge_plan import generate_challenge_plan
from shared.schemas.common import SessionStatus
from shared.schemas.session import CensusProfile
from shared.utils.logging import get_logger

logger = get_logger(__name__)

_FIELDS_ORDER = ["full_name", "dob_or_age", "gender", "locality", "household_size"]
_FIELD_KEYS = {
    "full_name": "ask_name",
    "dob_or_age": "ask_dob",
    "gender": "ask_gender",
    "locality": "ask_locality",
    "household_size": "ask_household",
}


def _next_empty_field(profile: CensusProfile) -> str | None:
    for field in _FIELDS_ORDER:
        if getattr(profile, field) is None:
            return field
    return None


async def ask_next_census_question(
    update: Update, context: ContextTypes.DEFAULT_TYPE, sess
) -> None:
    locale = context.user_data.get("locale", "en")
    field = _next_empty_field(sess.census_profile)
    if field is None:
        # All fields collected — ask confirmation
        text = build_confirmation_text(sess.census_profile, locale)
        await update.message.reply_text(text, parse_mode="Markdown")
        context.user_data["awaiting_confirmation"] = True
    else:
        key = _FIELD_KEYS[field]
        await update.message.reply_text(get_message(key, locale))
        context.user_data["current_census_field"] = field


async def census_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session_id = context.user_data.get("session_id")
    locale = context.user_data.get("locale", "en")
    if not session_id:
        return

    sess = get_session(session_id)
    if not sess or sess.status != SessionStatus.CENSUS_IN_PROGRESS:
        return

    # Handle confirmation
    if context.user_data.get("awaiting_confirmation"):
        text = (update.message.text or "").strip().lower()
        if text in {"confirm", "yes", "haan", "हाँ", "पुष्टि"}:
            sess.challenge_plan = generate_challenge_plan(sess.session_id)
            sess.status = SessionStatus.CHALLENGE_RUNNING
            update_session(sess)
            context.user_data.pop("awaiting_confirmation", None)
            await update.message.reply_text(get_message("profile_confirmed", locale))
            logger.info("census_complete", session_id=session_id)
            from apps.telegram.handlers.liveness_prompt import send_liveness_prompt
            await send_liveness_prompt(update, context, sess)
        else:
            # Restart census
            sess.census_profile = CensusProfile()
            update_session(sess)
            context.user_data.pop("awaiting_confirmation", None)
            await ask_next_census_question(update, context, sess)
        return

    # Handle field answer
    field = context.user_data.get("current_census_field")
    if not field:
        return

    raw = (update.message.text or "").strip()
    clarification = clarify_answer(field, raw, locale)
    if clarification:
        await update.message.reply_text(clarification)
        return

    profile_data = sess.census_profile.model_dump()
    if field == "household_size":
        try:
            profile_data[field] = int(raw)
        except ValueError:
            await update.message.reply_text(get_message("ask_household", locale))
            return
    else:
        profile_data[field] = raw

    sess.census_profile = CensusProfile(**profile_data)
    update_session(sess)
    logger.info("census_field_saved", session_id=session_id, field=field)
    await ask_next_census_question(update, context, sess)
