"""Telegram implementation of MessagingChannel (python-telegram-bot, async)."""
from __future__ import annotations

from typing import Optional

from kyc_bot.channels.base import Attachment, IncomingMessage


def normalize_update(update) -> Optional[IncomingMessage]:
    """Convert a python-telegram-bot Update into an IncomingMessage.

    Returns None for updates that carry nothing we handle (e.g. edited-message
    events, or empty updates). A tapped inline button arrives as a
    callback_query and is surfaced as text equal to the button's callback data,
    so the flow matches button taps and typed text the same way.
    """
    if getattr(update, "callback_query", None) is not None:
        cq = update.callback_query
        return IncomingMessage(user_id=str(cq.from_user.id), text=cq.data, attachment=None)

    message = getattr(update, "message", None)
    if message is None:
        return None

    user_id = str(message.from_user.id)

    if getattr(message, "photo", None):
        largest = message.photo[-1]  # PTB orders PhotoSize smallest -> largest
        return IncomingMessage(
            user_id=user_id,
            attachment=Attachment(kind="photo", file_id=largest.file_id),
        )

    if getattr(message, "video", None):
        v = message.video
        return IncomingMessage(
            user_id=user_id,
            attachment=Attachment(
                kind="video", file_id=v.file_id, file_name=getattr(v, "file_name", None)
            ),
        )

    if getattr(message, "document", None):
        d = message.document
        return IncomingMessage(
            user_id=user_id,
            attachment=Attachment(
                kind="document", file_id=d.file_id, file_name=getattr(d, "file_name", None)
            ),
        )

    if getattr(message, "text", None) is not None:
        return IncomingMessage(user_id=user_id, text=message.text)

    return None
