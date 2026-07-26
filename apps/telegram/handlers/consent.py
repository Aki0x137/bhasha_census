"""Consent accept/decline handlers — block all media until accepted (FR-002)."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from apps.api.db.session_store import get_session, update_session
from apps.telegram.i18n.messages import get_message
from shared.schemas.common import SessionStatus
from shared.utils.logging import get_logger

logger = get_logger(__name__)

_ACCEPT_WORDS = {"yes", "haan", "हाँ", "हां", "ok", "okay", "confirm", "agree", "consent"}
_DECLINE_WORDS = {"no", "nahi", "नहीं", "nope", "decline", "cancel", "exit"}


async def consent_response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session_id = context.user_data.get("session_id")
    locale = context.user_data.get("locale", "en")
    if not session_id:
        return

    sess = get_session(session_id)
    if not sess or sess.status != SessionStatus.CONSENT_PENDING:
        return

    text = (update.message.text or "").strip().lower()
    if text in _ACCEPT_WORDS:
        sess.consent_accepted = True
        sess.status = SessionStatus.CENSUS_IN_PROGRESS
        update_session(sess)
        await update.message.reply_text(get_message("consent_accepted", locale))
        # Kick off census
        from apps.telegram.handlers.census import ask_next_census_question
        await ask_next_census_question(update, context, sess)
        logger.info("consent_accepted", session_id=session_id)
    elif text in _DECLINE_WORDS:
        sess.status = SessionStatus.FAILED
        update_session(sess)
        await update.message.reply_text(get_message("consent_declined", locale))
        logger.info("consent_declined", session_id=session_id)


# Prevent media before consent
async def guard_media_before_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if media should be blocked (consent not yet given)."""
    session_id = context.user_data.get("session_id")
    locale = context.user_data.get("locale", "en")
    if not session_id:
        return True
    sess = get_session(session_id)
    if not sess or not sess.consent_accepted:
        await update.message.reply_text(get_message("consent_prompt", locale), parse_mode="Markdown")
        return True
    return False
