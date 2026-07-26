"""Voice challenge handler — Sarvam STT phrase match, typed SpeechEvidence (FR-007)."""
from __future__ import annotations

from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from apps.api.db.session_store import get_session, update_session
from apps.telegram.i18n.messages import get_message
from services.speech.phrase_verifier import verify_phrase
from shared.schemas.common import ReasonCode
from shared.utils.evidence_paths import session_speech_dir
from shared.utils.logging import get_logger

logger = get_logger(__name__)


def _active_speech_challenge(sess):
    for item in sess.challenge_plan:
        if not item.completed and item.challenge_type == "SAY_RANDOM_PHRASE":
            return item
    return None


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session_id = context.user_data.get("session_id")
    locale = context.user_data.get("locale", "en")
    if not session_id:
        return

    sess = get_session(session_id)
    if not sess or not sess.consent_accepted:
        await update.message.reply_text(get_message("consent_prompt", locale), parse_mode="Markdown")
        return

    challenge_item = _active_speech_challenge(sess)
    if not challenge_item:
        await update.message.reply_text("No active speech challenge right now.")
        return

    # Download voice
    speech_dir = session_speech_dir(session_id)
    audio_path = speech_dir / f"{challenge_item.challenge_id}.ogg"
    try:
        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive(str(audio_path))
    except Exception as exc:
        logger.error("voice_download_error", session_id=session_id, error=str(exc))
        await update.message.reply_text(get_message("media_error", locale))
        return

    # Build expected phrase from challenge engine
    from services.policy.challenge_engine import build_challenge_params
    from shared.schemas.common import ChallengeType
    params = build_challenge_params(challenge_item.challenge_id, ChallengeType.SAY_RANDOM_PHRASE)
    expected = params.expected_response or ""

    attempts_key = f"speech_attempts_{challenge_item.challenge_id}"
    attempts = context.user_data.get(attempts_key, 0) + 1
    context.user_data[attempts_key] = attempts
    max_attempts = params.max_attempts

    try:
        evidence = verify_phrase(
            audio_path, session_id, challenge_item.challenge_id,
            expected, locale=sess.locale,
        )
    except Exception as exc:
        logger.error("stt_error", session_id=session_id, error=str(exc))
        await update.message.reply_text(get_message("unexpected_error", locale))
        return

    sess.evidence_ids.append(evidence.evidence_id)

    if ReasonCode.SPEECH_MATCH_OK.value in evidence.reason_codes:
        challenge_item.completed = True
        challenge_item.outcome = "passed"
        update_session(sess)
        await update.message.reply_text(get_message("speech_match_ok", locale))
        logger.info("speech_challenge_passed", session_id=session_id)
    else:
        if attempts < max_attempts:
            await update.message.reply_text(
                get_message("speech_mismatch", locale, attempts_left=max_attempts - attempts)
            )
        else:
            challenge_item.completed = True
            challenge_item.outcome = "failed"
            update_session(sess)
            await update.message.reply_text(get_message("challenge_failed", locale))
