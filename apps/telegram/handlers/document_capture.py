"""Document capture handler — Sarvam digitization + field consistency (FR-008)."""
from __future__ import annotations

from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from apps.api.db.session_store import get_session, update_session
from apps.telegram.i18n.messages import get_message
from services.document.sarvam_digitize import get_doc_client
from services.document.field_matcher import build_document_evidence
from shared.schemas.common import ReasonCode
from shared.utils.evidence_paths import session_document_dir
from shared.utils.logging import get_logger

logger = get_logger(__name__)
_MAX_DOC_ATTEMPTS = 2


def _active_doc_challenge(sess):
    for item in sess.challenge_plan:
        if not item.completed and item.challenge_type == "SHOW_ID_AND_READ_FIELD":
            return item
    return None


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session_id = context.user_data.get("session_id")
    locale = context.user_data.get("locale", "en")
    if not session_id:
        return

    sess = get_session(session_id)
    if not sess or not sess.consent_accepted:
        await update.message.reply_text(get_message("consent_prompt", locale), parse_mode="Markdown")
        return

    challenge_item = _active_doc_challenge(sess)
    if not challenge_item:
        await update.message.reply_text("No document challenge active right now.")
        return

    attempts_key = f"doc_attempts_{challenge_item.challenge_id}"
    attempts = context.user_data.get(attempts_key, 0) + 1
    context.user_data[attempts_key] = attempts

    # Download photo
    doc_dir = session_document_dir(session_id)
    image_path = doc_dir / f"{challenge_item.challenge_id}_{attempts}.jpg"
    try:
        photo = update.message.photo[-1] if update.message.photo else None
        doc_file = update.message.document
        if photo:
            f = await photo.get_file()
        elif doc_file:
            f = await doc_file.get_file()
        else:
            await update.message.reply_text(get_message("doc_capture_prompt", locale))
            return
        await f.download_to_drive(str(image_path))
    except Exception as exc:
        logger.error("doc_download_error", session_id=session_id, error=str(exc))
        await update.message.reply_text(get_message("media_error", locale))
        return

    # Digitize
    try:
        result = get_doc_client().digitize(image_path)
    except Exception as exc:
        logger.error("sarvam_doc_error", session_id=session_id, error=str(exc))
        if attempts < _MAX_DOC_ATTEMPTS:
            await update.message.reply_text(
                get_message("doc_unreadable", locale, attempts_left=_MAX_DOC_ATTEMPTS - attempts)
            )
        else:
            challenge_item.completed = True
            challenge_item.outcome = "review"
            update_session(sess)
            await update.message.reply_text(get_message("doc_retry_exhausted", locale))
        return

    profile = sess.census_profile
    evidence = build_document_evidence(
        session_id,
        result,
        census_name=profile.full_name,
        census_dob=profile.dob_or_age,
        image_path=str(image_path),
    )
    sess.evidence_ids.append(evidence.evidence_id)

    if ReasonCode.DOC_UNREADABLE.value in evidence.reason_codes:
        if attempts < _MAX_DOC_ATTEMPTS:
            await update.message.reply_text(
                get_message("doc_unreadable", locale, attempts_left=_MAX_DOC_ATTEMPTS - attempts)
            )
        else:
            challenge_item.completed = True
            challenge_item.outcome = "review"
            update_session(sess)
            await update.message.reply_text(get_message("doc_retry_exhausted", locale))
        return

    challenge_item.completed = True
    challenge_item.outcome = "passed" if evidence.document_match_score >= 0.6 else "review"
    update_session(sess)
    await update.message.reply_text(get_message("doc_readable", locale))
    logger.info(
        "doc_processed",
        session_id=session_id,
        match_score=evidence.document_match_score,
        outcome=challenge_item.outcome,
    )
