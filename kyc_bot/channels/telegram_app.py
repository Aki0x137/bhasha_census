# kyc_bot/channels/telegram_app.py
"""Manual smoke-test entrypoint: an echo bot proving TelegramChannel works
end-to-end against real Telegram. Run with TELEGRAM_BOT_TOKEN set.

    TELEGRAM_BOT_TOKEN=... python -m kyc_bot.channels.telegram_app

This is NOT part of the KYC flow — it exists to validate the channel layer.
"""
from __future__ import annotations

import os

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from kyc_bot.channels.base import PromptButton
from kyc_bot.channels.telegram import TelegramChannel, normalize_update


async def _on_update(update: Update, context) -> None:
    msg = normalize_update(update)
    if msg is None:
        return
    channel = TelegramChannel(bot=context.bot)
    if update.callback_query is not None:
        await update.callback_query.answer()
    if msg.attachment is not None:
        data = await channel.download(msg.attachment)
        await channel.send_text(
            msg.user_id, f"Got {msg.attachment.kind}, {len(data)} bytes."
        )
    elif msg.text == "/start":
        await channel.send_prompt(
            msg.user_id,
            "Channel smoke test. Tap a button:",
            [PromptButton("Ping", "ping"), PromptButton("Pong", "pong")],
        )
    else:
        await channel.send_text(msg.user_id, f"echo: {msg.text}")


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, _on_update))
    app.add_handler(CallbackQueryHandler(_on_update))
    app.run_polling()


if __name__ == "__main__":
    main()
