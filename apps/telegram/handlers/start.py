"""Telegram /start handler — create or resume a single active session (FR-013)."""
from __future__ import annotations

import uuid
import time

from telegram import Update
from telegram.ext import ContextTypes

from apps.api.db.session_store import create_session, get_active_session_for_user
from apps.telegram.i18n.messages import get_message
from shared.schemas.session import EnrollmentSession
from shared.schemas.common import SessionStatus
from shared.utils.logging import get_logger

logger = get_logger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_ref = str(user.id)
    locale = "en"  # TODO: detect from user language_code

    existing = get_active_session_for_user(user_ref)
    if existing:
        context.user_data["session_id"] = existing.session_id
        context.user_data["locale"] = locale
        await update.message.reply_text(get_message("session_resumed", locale))
        logger.info("session_resumed", session_id=existing.session_id, user_ref=user_ref)
        # Re-prompt based on where the user left off
        from apps.telegram.handlers.liveness_prompt import send_liveness_prompt
        if existing.status in (SessionStatus.CHALLENGE_RUNNING, SessionStatus.CENSUS_COMPLETE):
            await send_liveness_prompt(update, context, existing)
        elif existing.status == SessionStatus.EVIDENCE_AGGREGATED:
            await update.message.reply_text(
                "✅ Liveness check recorded! Type /done to get your final enrollment verdict."
            )
        return

    session = EnrollmentSession(
        session_id=f"sess_{uuid.uuid4().hex[:12]}",
        user_ref=user_ref,
        status=SessionStatus.CONSENT_PENDING,
        locale=locale,
        created_at_ms=int(time.time() * 1000),
    )
    create_session(session)
    context.user_data["session_id"] = session.session_id
    context.user_data["locale"] = locale

    await update.message.reply_text(
        get_message("consent_prompt", locale),
        parse_mode="Markdown",
    )
    logger.info("session_created", session_id=session.session_id, user_ref=user_ref)
