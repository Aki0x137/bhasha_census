# bhasaha_census

Local-first MVP for video liveness and human-vs-AI media verification
(Linux and macOS).

- **Architecture & MVP design**: [`docs/liveliness_check_mvp.md`](docs/liveliness_check_mvp.md)
- **Project constitution** (scope, stack, contracts, decision authority):
  [`.specify/memory/constitution.md`](.specify/memory/constitution.md)

**Stack (constitution)**: Python + pip, Temporal, LangGraph, typed Pydantic
contracts, FastAPI, Sarvam (speech/docs), AWS Bedrock (orchestration),
local video workers, SQLite + filesystem evidence.

## Run the Telegram channel (smoke test)

1. Create a bot with @BotFather and copy the token.
2. Install: `python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
3. Run the echo smoke test:

   ```bash
   TELEGRAM_BOT_TOKEN=<your-token> .venv/bin/python -m kyc_bot.channels.telegram_app
   ```

4. Message the bot: `/start` shows buttons; sending a photo/video/document
   replies with the byte count; any text is echoed. This exercises the whole
   `MessagingChannel` surface (send_text, send_prompt, download).
