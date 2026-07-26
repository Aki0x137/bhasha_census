"""TEMP /verify command — full liveness check via browser webapp or static photo fallback.

Usage:
  1. /verify  → sends a button linking to the liveness web page (preferred)
             → if WEBAPP_URL not set, falls back to photo-based challenge

The liveness page (http://localhost:8000/liveness or WEBAPP_URL/liveness) captures
real webcam frames, runs the full plugin pipeline, and shows scores in the browser.
"""
from __future__ import annotations

import os
import time
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from apps.api.db.session_store import (
    create_session,
    get_active_session_for_user,
    get_session,
    update_session,
)
from shared.schemas.common import ChallengeType, SessionStatus
from shared.schemas.session import ChallengePlanItem, EnrollmentSession
from shared.utils.logging import get_logger

logger = get_logger(__name__)

_TEMP_CHALLENGE = ChallengeType.LOOK_LEFT_RIGHT

_CHALLENGES = {
    ChallengeType.LOOK_LEFT_RIGHT: ("👀 Look Left / Right", "Slowly turn your head left, then right."),
    ChallengeType.BLINK_TWICE:     ("👁 Blink Twice",       "Blink twice, slowly and clearly."),
    ChallengeType.SMILE_AND_TILT:  ("😊 Smile & Tilt",      "Smile and tilt your head slightly."),
}


def _liveness_url(session_id: str, chat_id: int | str) -> str:
    """Return the liveness page URL with session and chat context embedded."""
    base = os.environ.get("WEBAPP_URL", "").rstrip("/")
    if not base:
        base = "http://localhost:8000"
    return f"{base}/liveness?session_id={session_id}&chat_id={chat_id}"


async def verify_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send liveness challenge link (Mini App button) or fallback photo prompt."""
    user = update.effective_user
    user_ref = str(user.id)
    locale = context.user_data.get("locale", "en")

    # Create / reuse session
    sess = get_active_session_for_user(user_ref)
    if sess is None:
        sess = EnrollmentSession(
            session_id=f"sess_{uuid.uuid4().hex[:12]}",
            user_ref=user_ref,
            locale=locale,
            created_at_ms=int(time.time() * 1000),
        )
        create_session(sess)
    else:
        sess = get_session(sess.session_id) or sess

    challenge_id = f"{sess.session_id}_temp_verify"

    sess.consent_accepted = True
    sess.status = SessionStatus.CHALLENGE_RUNNING
    sess.challenge_plan = [
        ChallengePlanItem(
            challenge_id=challenge_id,
            challenge_type=_TEMP_CHALLENGE.value,
            completed=False,
        )
    ]
    update_session(sess)

    context.user_data["session_id"] = sess.session_id
    context.user_data["locale"] = locale
    context.user_data["temp_verify"] = True
    context.user_data.pop(f"attempts_{challenge_id}", None)

    chat_id = update.effective_chat.id
    liveness_url = _liveness_url(sess.session_id, chat_id)
    webapp_url = os.environ.get("WEBAPP_URL", "").rstrip("/")

    intro = (
        "🎥 *Liveness Check*\n\n"
        "This verifies you are a real live person.\n"
        "The full check captures multiple webcam frames and runs:\n"
        "• Face detection\n"
        "• Image quality scoring\n"
        "• Anti-spoof / anti-replay\n"
        "• Pose / blink / mouth-movement plugins\n\n"
    )

    # Always open in the system browser (url=), NOT as a Telegram Mini App (web_app=).
    # Desktop Telegram WebView blocks getUserMedia; Chrome/Safari do not.
    if webapp_url.startswith("https://"):
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🌐 Open Liveness in Browser", url=liveness_url),
        ]])
        await update.message.reply_text(
            intro
            + "Tap the button to open Chrome/Safari (not Telegram's built-in WebView).\n"
            + "Allow camera when prompted.\n\n"
            + f"`Session: {sess.session_id}`",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        # Localhost / non-HTTPS — Telegram rejects url= buttons for these.
        await update.message.reply_text(
            intro
            + "Open this URL in *Chrome or Safari* (not Telegram):\n"
            f"{liveness_url}\n\n"
            "If camera is blocked, use *Upload photo* on that page, "
            "or send a photo/video here.\n\n"
            f"`Session: {sess.session_id}`",
            parse_mode="Markdown",
        )

    logger.info("temp_verify_started", session_id=sess.session_id, user_ref=user_ref, url=liveness_url)


def format_verify_report(evidence) -> str:
    """Human-readable pipeline dump for Telegram photo/video fallback reply."""
    scores = evidence.scores
    plugins = ", ".join(
        f"{p.plugin_name}({'ok' if p.ok else 'fail'})" for p in evidence.plugin_results
    ) or "none"
    targets = "\n".join(
        f"  • {t.target_id}: {t.status.value}"
        + (f" ({t.detail})" if t.detail else "")
        for t in evidence.targets_evaluation
    ) or "  (none)"
    reasons = ", ".join(evidence.reason_codes) or "—"
    outcome = "FAIL" if scores.hard_fail_hint else "PASS"

    return (
        f"📊 *Video pipeline result: {outcome}*\n\n"
        f"face_present=`{scores.face_present}`  face_count=`{scores.face_count}`\n"
        f"quality=`{scores.quality_score:.2f}`  spoof=`{scores.spoof_score:.2f}`\n"
        f"hard_fail_hint=`{scores.hard_fail_hint}`\n"
        f"reasons: `{reasons}`\n\n"
        f"plugins: {plugins}\n"
        f"targets:\n{targets}\n\n"
        f"evidence_id: `{evidence.evidence_id}`\n\n"
        "_For the full webcam challenge, use /verify and open the browser link._"
    )
