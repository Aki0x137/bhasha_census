"""Telegram bot entrypoint and config loader."""
from __future__ import annotations

import os

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from apps.telegram.handlers.start import start_handler
from apps.telegram.handlers.consent import consent_response_handler
from apps.telegram.handlers.census import census_answer_handler
from apps.telegram.handlers.presence_challenge import (
    photo_handler,
    video_handler,
    challenge_timeout_handler,
)
from apps.telegram.handlers.speech_challenge import voice_handler
from apps.telegram.handlers.document_capture import document_handler
from apps.telegram.handlers.finalize import finalize_handler
from apps.telegram.handlers.verify import verify_handler
from shared.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def build_app() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("done", finalize_handler))
    # TEMP: skip enrollment and smoke-test video pipeline E2E
    app.add_handler(CommandHandler("verify", verify_handler))
    # Text message router (consent → census → generic)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _text_router))
    # Media handlers
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, video_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

    return app


async def _text_router(update, context):
    from apps.api.db.session_store import get_session
    from shared.schemas.common import SessionStatus

    session_id = context.user_data.get("session_id")
    if not session_id:
        await start_handler(update, context)
        return
    sess = get_session(session_id)
    if not sess:
        return
    if sess.status == SessionStatus.CONSENT_PENDING:
        await consent_response_handler(update, context)
    elif sess.status == SessionStatus.CENSUS_IN_PROGRESS:
        await census_answer_handler(update, context)
    else:
        await update.message.reply_text("Use /done when you're ready to receive your verdict.")


def main() -> None:
    import asyncio

    # Python 3.14+: no implicit event loop on MainThread
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = build_app()
    logger.info("bot_starting")
    app.run_polling()


if __name__ == "__main__":
    main()
