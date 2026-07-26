"""Presence challenge handlers — photo/video, retry, multi-face, timeout (FR-006, M6)."""
from __future__ import annotations

from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from apps.api.db.session_store import get_session, update_session
from apps.telegram.i18n.messages import get_message
from apps.telegram.services.job_builder import build_video_job
from services.video import plugins  # noqa: F401
from services.video.pipeline import run_verification_job
from shared.schemas.common import ChallengeType, ReasonCode
from shared.utils.evidence_paths import session_video_dir
from shared.utils.logging import get_logger

logger = get_logger(__name__)


async def _download_media(file_obj, dest: Path) -> None:
    f = await file_obj.get_file()
    await f.download_to_drive(str(dest))


def _active_challenge(sess):
    """Return the first incomplete challenge plan item, or None."""
    for item in sess.challenge_plan:
        if not item.completed and item.challenge_type not in (
            "SAY_RANDOM_PHRASE", "SHOW_ID_AND_READ_FIELD"
        ):
            return item
    return None


async def _run_presence_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE, file_obj) -> None:
    session_id = context.user_data.get("session_id")
    locale = context.user_data.get("locale", "en")
    if not session_id:
        return

    sess = get_session(session_id)
    if not sess or not sess.consent_accepted:
        await update.message.reply_text(get_message("consent_prompt", locale), parse_mode="Markdown")
        return

    challenge_item = _active_challenge(sess)
    if not challenge_item:
        await update.message.reply_text("No active presence challenge. Please wait for instructions.")
        return

    # Download media
    vid_dir = session_video_dir(session_id)
    media_path = vid_dir / f"{challenge_item.challenge_id}.jpg"
    try:
        await _download_media(file_obj, media_path)
    except Exception as exc:
        logger.error("media_download_error", session_id=session_id, error=str(exc))
        await update.message.reply_text(get_message("media_error", locale))
        return

    # Build and run job
    job = build_video_job(
        sess,
        challenge_item.challenge_id,
        ChallengeType(challenge_item.challenge_type),
        media_path,
    )
    try:
        evidence = run_verification_job(job)
    except FileNotFoundError as exc:
        await update.message.reply_text(get_message("media_error", locale))
        return
    except Exception as exc:
        logger.error("pipeline_error", session_id=session_id, error=str(exc))
        await update.message.reply_text(get_message("unexpected_error", locale))
        return

    sess.evidence_ids.append(evidence.evidence_id)
    attempts_key = f"attempts_{challenge_item.challenge_id}"
    attempts = context.user_data.get(attempts_key, 0) + 1
    context.user_data[attempts_key] = attempts
    max_attempts = job.params.max_attempts
    temp_verify = bool(context.user_data.get("temp_verify"))

    async def _reply_outcome(default_text: str) -> None:
        if temp_verify:
            from apps.telegram.handlers.verify import format_verify_report

            await update.message.reply_text(format_verify_report(evidence), parse_mode="Markdown")
        else:
            await update.message.reply_text(default_text)

    # Multi-face check (M6)
    if ReasonCode.MULTI_FACE.value in evidence.reason_codes:
        if attempts < max_attempts and not temp_verify:
            await update.message.reply_text(get_message("challenge_multi_face", locale))
        else:
            challenge_item.completed = True
            challenge_item.outcome = "failed"
            update_session(sess)
            await _reply_outcome(get_message("challenge_failed", locale))
            if temp_verify:
                context.user_data.pop("temp_verify", None)
        return

    if evidence.scores.hard_fail_hint:
        if attempts < max_attempts and not temp_verify:
            await update.message.reply_text(
                get_message("challenge_retry", locale, attempts_left=max_attempts - attempts)
            )
        else:
            challenge_item.completed = True
            challenge_item.outcome = "failed"
            update_session(sess)
            await _reply_outcome(get_message("challenge_failed", locale))
            if temp_verify:
                context.user_data.pop("temp_verify", None)
    else:
        challenge_item.completed = True
        challenge_item.outcome = "passed"
        update_session(sess)
        await _reply_outcome(get_message("challenge_passed", locale))
        if temp_verify:
            context.user_data.pop("temp_verify", None)
        logger.info("challenge_passed", session_id=session_id, challenge_id=challenge_item.challenge_id)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]  # highest resolution
    await _run_presence_challenge(update, context, photo)


async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video = update.message.video or update.message.video_note
    await _run_presence_challenge(update, context, video)


async def challenge_timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    locale = context.user_data.get("locale", "en")
    await update.message.reply_text(get_message("challenge_failed", locale))
