# kyc_bot/app.py
"""Real SIR registration bot entrypoint (long-polling).

Requires env vars:
  TELEGRAM_BOT_TOKEN  - the bot token from @BotFather
  KYC_MASTER_KEY      - a Fernet key (see kyc_bot.storage.crypto.load_key)

Run:
    TELEGRAM_BOT_TOKEN=... KYC_MASTER_KEY=... python -m kyc_bot.app
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from kyc_bot import config
from kyc_bot.channels.telegram import TelegramChannel, normalize_update
from kyc_bot.flow.session_store import InMemorySessionStore
from kyc_bot.flow.sir_flow import SirFlow
from kyc_bot.storage import crypto
from kyc_bot.storage.db import SubmissionStore
from kyc_bot.storage.vault import Vault


def build_flow(channel: TelegramChannel) -> SirFlow:
    key = crypto.load_key()
    return SirFlow(
        channel=channel,
        sessions=InMemorySessionStore(),
        vault=Vault(root=config.vault_dir(), key=key),
        submissions=SubmissionStore(config.db_path(), key=key),
        ref_factory=lambda: secrets.token_hex(4).upper(),
        now=lambda: datetime.now(timezone.utc).isoformat(),
    )


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    # One flow instance shared across updates (in-memory sessions persist
    # for the process lifetime).
    flow_holder: dict[str, SirFlow] = {}

    async def on_update(update: Update, context) -> None:
        msg = normalize_update(update)
        if msg is None:
            return
        if update.callback_query is not None:
            await update.callback_query.answer()
        if "flow" not in flow_holder:
            flow_holder["flow"] = build_flow(TelegramChannel(bot=context.bot))
        await flow_holder["flow"].handle(msg)

    app.add_handler(MessageHandler(filters.ALL, on_update))
    app.add_handler(CallbackQueryHandler(on_update))
    app.run_polling()


if __name__ == "__main__":
    main()
