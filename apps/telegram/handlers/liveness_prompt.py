"""Reusable helper: build and send the liveness challenge URL to a user.

Used by census.py (after census confirmation), start.py (on session resume),
and the text router (when the user texts while a challenge is pending).
"""
from __future__ import annotations

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from shared.schemas.session import EnrollmentSession
from shared.utils.logging import get_logger

logger = get_logger(__name__)

_PHYSICAL_CHALLENGE_TYPES = {"LOOK_LEFT_RIGHT", "BLINK_TWICE", "SMILE_AND_TILT"}

_CHALLENGE_LABELS = {
    "LOOK_LEFT_RIGHT": "👀 Look Left & Right",
    "BLINK_TWICE": "👁 Blink Twice",
    "SMILE_AND_TILT": "😊 Smile & Tilt",
}


def liveness_url(session_id: str, chat_id: int | str) -> str:
    """Build the liveness page URL with session context embedded."""
    base = os.environ.get("WEBAPP_URL", "").rstrip("/") or "http://localhost:8000"
    return f"{base}/liveness?session_id={session_id}&chat_id={chat_id}"


async def send_liveness_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    sess: EnrollmentSession,
) -> None:
    """Send the liveness challenge link as an inline button (https) or plain URL (localhost)."""
    chat_id = update.effective_chat.id

    # Pick the first pending physical challenge from the plan, fallback to LOOK_LEFT_RIGHT
    challenge_type = "LOOK_LEFT_RIGHT"
    for item in sess.challenge_plan:
        if item.challenge_type in _PHYSICAL_CHALLENGE_TYPES and not item.completed:
            challenge_type = item.challenge_type
            break

    label = _CHALLENGE_LABELS.get(challenge_type, challenge_type)
    url = liveness_url(sess.session_id, chat_id)
    webapp_url = os.environ.get("WEBAPP_URL", "").rstrip("/")

    prompt = (
        f"🎥 *Liveness Challenge: {label}*\n\n"
        "1. Open the link below in *Chrome or Safari*\n"
        "   (not Telegram's built-in browser — camera won't work there)\n"
        "2. Allow camera access when prompted\n"
        "3. Follow the on-screen instruction\n"
        "4. Results will appear here automatically\n\n"
        f"Session: `{sess.session_id}`"
    )

    if webapp_url.startswith("https://"):
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🌐 Open Liveness Check", url=url),
        ]])
        await update.message.reply_text(
            prompt, parse_mode="Markdown", reply_markup=keyboard
        )
    else:
        # Localhost: Telegram rejects non-https inline buttons; send plain text
        await update.message.reply_text(
            prompt + f"\n\n📎 `{url}`",
            parse_mode="Markdown",
        )

    logger.info("liveness_prompt_sent", session_id=sess.session_id, challenge=challenge_type)
