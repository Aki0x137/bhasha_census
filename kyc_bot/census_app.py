"""Bhasha Census bot — walks the census questionnaire over Telegram.

Run:

    # .env holds TELEGRAM_BOT_TOKEN (+ optional SARVAM_API_KEY, WEBAPP_URL)
    python -m kyc_bot.census_app

Flow: /start -> consent -> household questions -> head questions -> upload ID
(OCR + masked + name-consistency confirm) -> liveness Mini App -> summary record.

Demo guardrails: sample/own data only; ID numbers masked to last-4; no real
government/KYC backend; name mismatches are surfaced for human review, never
auto-rejected.
"""
from __future__ import annotations

import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from kyc_bot.channels.base import PromptButton
from kyc_bot.channels.telegram import TelegramChannel, normalize_update
from kyc_bot.flow.actions import RequestPhoto, SendButtons, SendText, SendWebApp
from kyc_bot.flow.engine import OcrAnswer, QuestionnaireEngine
from kyc_bot.flow.session import InMemorySessionStore
from kyc_bot.storage import census_db
from kyc_bot.verification.ocr import (
    FakeDocProvider,
    SarvamDocProvider,
    mask_id,
    name_similarity,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("census_bot")

_store = InMemorySessionStore()
_engine = QuestionnaireEngine()


def _load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader (no extra dependency). Existing env vars win."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _doc_provider():
    # Default to the reliable sample OCR for the live demo. Set DOC_PROVIDER=sarvam
    # (with SARVAM_API_KEY) to attempt the real Doc-AI job (falls back on any error).
    mode = os.getenv("DOC_PROVIDER", "fake").lower()
    key = os.getenv("SARVAM_API_KEY")
    if mode == "sarvam" and key:
        log.info("OCR: Sarvam Doc-AI (with sample fallback).")
        return SarvamDocProvider(key)
    log.info("OCR: FakeDocProvider (sample, offline, deterministic).")
    return FakeDocProvider()


async def _render(channel: TelegramChannel, user_id: str, actions) -> None:
    for action in actions:
        if isinstance(action, SendText):
            await channel.send_text(user_id, action.text)
        elif isinstance(action, RequestPhoto):
            await channel.send_text(user_id, action.text)
        elif isinstance(action, SendButtons):
            await channel.send_prompt(
                user_id, action.text, [PromptButton(lbl, val) for lbl, val in action.buttons]
            )
        elif isinstance(action, SendWebApp):
            if action.url:
                await channel.send_webapp(user_id, action.text, action.label, action.url)
                await channel.send_prompt(
                    user_id,
                    "When the liveness check is done, tap Continue.",
                    [PromptButton("Continue ✅", "__continue__")],
                )
            else:
                await channel.send_prompt(
                    user_id,
                    action.text + "\n(Liveness Mini App not configured — tap Continue to finish.)",
                    [PromptButton("Continue ✅", "__continue__")],
                )


async def on_start(update: Update, context) -> None:
    channel = TelegramChannel(bot=context.bot)
    user_id = str(update.effective_user.id)
    session = _store.reset(user_id, webapp_url=os.getenv("WEBAPP_URL"))
    await channel.send_text(
        user_id,
        "🧾 *Bhasha Census* — a quick household survey.\n"
        "Demo only: please use sample or your own data.",
    )
    await _render(channel, user_id, _engine.next_actions(session))


async def on_update(update: Update, context) -> None:
    msg = normalize_update(update)
    if msg is None:
        return
    channel = TelegramChannel(bot=context.bot)
    if update.callback_query is not None:
        await update.callback_query.answer()

    session = _store.get_or_create(msg.user_id, webapp_url=os.getenv("WEBAPP_URL"))
    q = _engine.current(session)
    if q is None:
        await channel.send_text(msg.user_id, "Survey complete. Send /start to begin again.")
        return

    if q.qtype == "photo_ocr" and not session.awaiting_confirm and msg.attachment is not None:
        await channel.send_text(msg.user_id, "📄 Reading the card…")
        provider = context.application.bot_data["doc_provider"]
        raw = await provider.digitize(await channel.download(msg.attachment))
        answer = OcrAnswer(
            masked_id=mask_id(raw.id_number),
            ocr_name=raw.name,
            name_match=name_similarity(raw.name, session.record.head.name),
        )
        actions = _engine.submit(session, ocr=answer)
    else:
        actions = _engine.submit(session, text=msg.text)

    _store.save(session)

    # Persist the completed record once, for the admin approval queue.
    done = _engine.current(session) is None
    if done and session.record.consent and not session.declined and not session.saved:
        try:
            rid = census_db.insert_record(session.record, user_id=msg.user_id)
            session.saved = True
            log.info("census record persisted (id=%s)", rid)
        except Exception as exc:  # noqa: BLE001 - persistence must not break the chat
            log.warning("failed to persist census record: %s", exc)

    await _render(channel, msg.user_id, actions)


def main() -> None:
    _load_dotenv()
    census_db.init_db()
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.bot_data["doc_provider"] = _doc_provider()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, on_update))
    app.add_handler(CallbackQueryHandler(on_update))
    log.info("Bhasha Census bot running (long-polling). Ctrl-C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
