"""Finalize Telegram handler — /done command triggers verdict (FR-009)."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from apps.api.db.session_store import get_session, update_session
from apps.telegram.i18n.messages import get_message
from services.orchestrator.finalize import finalize_enrollment
from shared.schemas.common import EnrollmentVerdict, SessionStatus
from shared.utils.logging import get_logger

logger = get_logger(__name__)

_VERDICT_MSG_KEY = {
    EnrollmentVerdict.APPROVED: "verdict_approved",
    EnrollmentVerdict.NEEDS_REVIEW: "verdict_needs_review",
    EnrollmentVerdict.REJECTED: "verdict_rejected",
    EnrollmentVerdict.NEEDS_MORE_EVIDENCE: "verdict_needs_more_evidence",
}


async def finalize_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session_id = context.user_data.get("session_id")
    locale = context.user_data.get("locale", "en")

    if not session_id:
        await update.message.reply_text("No active session. Send /start to begin.")
        return

    sess = get_session(session_id)
    if not sess:
        await update.message.reply_text("Session not found. Send /start to begin.")
        return
    if sess.status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.EXPIRED):
        await update.message.reply_text("Your enrollment is already finalized.")
        return

    await update.message.reply_text("Processing your enrollment... please wait.")

    try:
        decision = await finalize_enrollment(sess)
    except Exception as exc:
        logger.error("finalize_error", session_id=session_id, error=str(exc))
        await update.message.reply_text(get_message("unexpected_error", locale))
        return

    sess.final_verdict = decision.verdict.value
    sess.status = SessionStatus.COMPLETED
    update_session(sess)

    reasons = ", ".join(decision.reason_codes[:3]) if decision.reason_codes else "—"
    msg_key = _VERDICT_MSG_KEY.get(decision.verdict, "verdict_needs_review")
    await update.message.reply_text(
        get_message(msg_key, locale, reasons=reasons),
        parse_mode="Markdown",
    )
    logger.info(
        "finalize_sent",
        session_id=session_id,
        verdict=decision.verdict.value,
        confidence=decision.confidence,
    )
