"""Telegram implementation of MessagingChannel (python-telegram-bot, async)."""
from __future__ import annotations

from typing import Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from kyc_bot.channels.base import (
    Attachment,
    IncomingMessage,
    MessagingChannel,
    PromptButton,
)


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


class TelegramChannel(MessagingChannel):
    """MessagingChannel backed by a python-telegram-bot Bot.

    The Bot is injected so tests can pass a mock and production can pass a
    real Bot built from a token. Inbound updates are normalized elsewhere via
    normalize_update; this class covers the outbound surface + downloads.
    """

    def __init__(self, bot: Bot):
        self._bot = bot

    async def send_text(self, user_id: str, text: str) -> None:
        await self._bot.send_message(chat_id=int(user_id), text=text)

    async def send_prompt(
        self, user_id: str, text: str, buttons: list[PromptButton]
    ) -> None:
        row = [InlineKeyboardButton(b.label, callback_data=b.value) for b in buttons]
        markup = InlineKeyboardMarkup([row])
        await self._bot.send_message(chat_id=int(user_id), text=text, reply_markup=markup)

    async def download(self, attachment: Attachment) -> bytes:
        tg_file = await self._bot.get_file(attachment.file_id)
        data = await tg_file.download_as_bytearray()
        return bytes(data)
