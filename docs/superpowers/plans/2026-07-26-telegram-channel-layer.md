# Telegram Channel Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the channel abstraction (`MessagingChannel`) and a working Telegram implementation (`TelegramChannel`) so a future KYC flow can drive conversations without knowing which chat platform is underneath.

**Architecture:** A `MessagingChannel` abstract base defines everything the flow needs from a chat platform: receive messages (text + media attachments), send text, send a prompt with tappable buttons, and download an uploaded file's bytes. `TelegramChannel` implements this over `python-telegram-bot` (async, long-polling). All platform-specific types are normalized into channel-neutral dataclasses (`IncomingMessage`, `Attachment`, `PromptButton`) so nothing above the channel layer imports Telegram types. Tests mock `python-telegram-bot` objects so no live bot token or network is needed.

**Tech Stack:** Python 3.11–3.12 (avoid 3.14 — ML libs used in later slices lack wheels), `python-telegram-bot` v21 (async), `pytest` + `pytest-asyncio`, `ruff` for lint.

**Scope note:** This slice is the channel layer ONLY. No KYC state machine, no verification, no storage. The flow layer will consume this interface in a later plan.

**Repo note:** This repo's `.gitignore` ignores `docs/`. Committing plan/spec docs may require `git add -f`. The `.specify/` and `.cursor/` tooling in this repo is unrelated — do not modify it.

---

### Task 1: Project scaffolding & dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `kyc_bot/__init__.py`
- Create: `kyc_bot/channels/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/channels/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "kyc-bot"
version = "0.1.0"
description = "Open-source zero-infra KYC identity proofing over chat"
requires-python = ">=3.11,<3.13"
dependencies = [
    "python-telegram-bot==21.6",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.3",
    "pytest-asyncio==0.24.0",
    "ruff==0.6.9",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["kyc_bot*"]
```

- [ ] **Step 2: Create `requirements.txt`**

```
python-telegram-bot==21.6
pytest==8.3.3
pytest-asyncio==0.24.0
ruff==0.6.9
```

- [ ] **Step 3: Create the four empty package markers**

Create `kyc_bot/__init__.py` with contents:

```python
"""KYC bot — open-source identity proofing over chat."""
```

Create `kyc_bot/channels/__init__.py`, `tests/__init__.py`, `tests/channels/__init__.py` each as an empty file (zero bytes).

- [ ] **Step 4: Create a virtualenv and install**

Run:
```bash
cd ~/bhasaha_census
python3.12 -m venv .venv || python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```
Expected: installs `python-telegram-bot`, `pytest`, `pytest-asyncio`, `ruff` with no errors. (`.venv/` is already gitignored.)

- [ ] **Step 5: Verify pytest runs (collects zero tests)**

Run: `.venv/bin/pytest -q`
Expected: `no tests ran` (exit code 5 is fine — no tests yet).

- [ ] **Step 6: Commit**

```bash
git add -f pyproject.toml requirements.txt kyc_bot/ tests/
git commit -m "chore: scaffold kyc_bot package and channel layer test dirs"
```

---

### Task 2: Channel-neutral data types

**Files:**
- Create: `kyc_bot/channels/base.py`
- Test: `tests/channels/test_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/channels/test_types.py
from kyc_bot.channels.base import Attachment, IncomingMessage, PromptButton


def test_attachment_holds_kind_and_file_id():
    att = Attachment(kind="photo", file_id="AgACAgID", file_name=None)
    assert att.kind == "photo"
    assert att.file_id == "AgACAgID"
    assert att.file_name is None


def test_incoming_message_text_only():
    msg = IncomingMessage(user_id="42", text="hello", attachment=None)
    assert msg.user_id == "42"
    assert msg.text == "hello"
    assert msg.attachment is None


def test_incoming_message_with_attachment():
    att = Attachment(kind="video", file_id="BAACAg", file_name="clip.mp4")
    msg = IncomingMessage(user_id="42", text=None, attachment=att)
    assert msg.attachment.kind == "video"
    assert msg.text is None


def test_prompt_button_label_and_value():
    btn = PromptButton(label="I agree", value="consent_yes")
    assert btn.label == "I agree"
    assert btn.value == "consent_yes"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/channels/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError: cannot import name 'Attachment'`.

- [ ] **Step 3: Write minimal implementation**

```python
# kyc_bot/channels/base.py
"""Channel abstraction: platform-neutral messaging interface and types.

Nothing above the channel layer should import platform SDK types (e.g.
python-telegram-bot). Channels normalize platform events into these
dataclasses and accept these dataclasses when sending.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional

AttachmentKind = Literal["photo", "video", "document"]


@dataclass(frozen=True)
class Attachment:
    """A media file the user sent. `file_id` is a channel-scoped handle used
    to download the bytes later via MessagingChannel.download."""
    kind: AttachmentKind
    file_id: str
    file_name: Optional[str] = None


@dataclass(frozen=True)
class IncomingMessage:
    """A normalized inbound message. Exactly one of text/attachment is the
    meaningful payload for a given message, but both fields always exist."""
    user_id: str
    text: Optional[str] = None
    attachment: Optional[Attachment] = None


@dataclass(frozen=True)
class PromptButton:
    """A tappable choice. `label` is shown to the user; `value` is the stable
    token the flow matches on when the user taps it."""
    label: str
    value: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/channels/test_types.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add kyc_bot/channels/base.py tests/channels/test_types.py
git commit -m "feat: add channel-neutral message and prompt data types"
```

---

### Task 3: MessagingChannel interface

**Files:**
- Modify: `kyc_bot/channels/base.py` (append the ABC)
- Test: `tests/channels/test_base.py`

- [ ] **Step 1: Write the failing test**

This test defines a trivial in-memory `FakeChannel` subclass to prove the interface is implementable and that a class missing a method cannot be instantiated.

```python
# tests/channels/test_base.py
import pytest

from kyc_bot.channels.base import (
    Attachment,
    IncomingMessage,
    MessagingChannel,
    PromptButton,
)


class FakeChannel(MessagingChannel):
    def __init__(self):
        self.sent_texts: list[tuple[str, str]] = []
        self.sent_prompts: list[tuple[str, str, list[PromptButton]]] = []
        self.files: dict[str, bytes] = {}

    async def send_text(self, user_id: str, text: str) -> None:
        self.sent_texts.append((user_id, text))

    async def send_prompt(self, user_id: str, text: str, buttons: list[PromptButton]) -> None:
        self.sent_prompts.append((user_id, text, buttons))

    async def download(self, attachment: Attachment) -> bytes:
        return self.files[attachment.file_id]


async def test_fake_channel_send_text():
    ch = FakeChannel()
    await ch.send_text("42", "hi")
    assert ch.sent_texts == [("42", "hi")]


async def test_fake_channel_send_prompt():
    ch = FakeChannel()
    btns = [PromptButton("Yes", "y"), PromptButton("No", "n")]
    await ch.send_prompt("42", "Agree?", btns)
    assert ch.sent_prompts == [("42", "Agree?", btns)]


async def test_fake_channel_download():
    ch = FakeChannel()
    ch.files["fid1"] = b"\x89PNG"
    data = await ch.download(Attachment(kind="photo", file_id="fid1"))
    assert data == b"\x89PNG"


def test_cannot_instantiate_incomplete_subclass():
    class Broken(MessagingChannel):
        async def send_text(self, user_id: str, text: str) -> None:
            ...
        # missing send_prompt and download

    with pytest.raises(TypeError):
        Broken()


def test_incoming_message_is_reexported():
    # sanity: the flow layer imports everything from base
    assert IncomingMessage(user_id="1").user_id == "1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/channels/test_base.py -v`
Expected: FAIL with `ImportError: cannot import name 'MessagingChannel'`.

- [ ] **Step 3: Append the ABC to `kyc_bot/channels/base.py`**

Add this to the end of the existing file (keep the dataclasses above it):

```python
class MessagingChannel(ABC):
    """Everything the KYC flow needs from a chat platform.

    Inbound messages are delivered by the concrete channel (e.g. via a
    handler registered on the platform SDK) as normalized IncomingMessage
    objects; how they reach the flow is the channel's concern. The methods
    below are what the flow calls outbound. A concrete channel must implement
    all three."""

    @abstractmethod
    async def send_text(self, user_id: str, text: str) -> None:
        """Send a plain text message to the user."""

    @abstractmethod
    async def send_prompt(
        self, user_id: str, text: str, buttons: list[PromptButton]
    ) -> None:
        """Send `text` with a set of tappable buttons. When the user taps
        one, the channel delivers an IncomingMessage whose `text` equals the
        chosen button's `value`."""

    @abstractmethod
    async def download(self, attachment: Attachment) -> bytes:
        """Fetch the raw bytes for a previously received attachment."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/channels/test_base.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: 9 passed (4 from test_types + 5 here).

- [ ] **Step 6: Commit**

```bash
git add kyc_bot/channels/base.py tests/channels/test_base.py
git commit -m "feat: add MessagingChannel abstract interface"
```

---

### Task 4: TelegramChannel — normalizing inbound updates

**Files:**
- Create: `kyc_bot/channels/telegram.py`
- Test: `tests/channels/test_telegram.py`

This task builds a pure function that converts a `python-telegram-bot` `Update` into our `IncomingMessage`, tested with mocked PTB objects (no network).

- [ ] **Step 1: Write the failing test**

```python
# tests/channels/test_telegram.py
from types import SimpleNamespace

from kyc_bot.channels.base import IncomingMessage
from kyc_bot.channels.telegram import normalize_update


def _update(user_id=42, text=None, photo=None, video=None, document=None, callback=None):
    """Build a minimal object shaped like a PTB Update for normalize_update."""
    message = None
    if text is not None or photo or video or document:
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=user_id),
            text=text,
            photo=photo or [],       # PTB gives a list of PhotoSize; last is largest
            video=video,
            document=document,
        )
    callback_query = None
    if callback is not None:
        callback_query = SimpleNamespace(
            from_user=SimpleNamespace(id=user_id),
            data=callback,
        )
    return SimpleNamespace(message=message, callback_query=callback_query)


def test_normalize_text_message():
    msg = normalize_update(_update(text="hello"))
    assert msg == IncomingMessage(user_id="42", text="hello", attachment=None)


def test_normalize_photo_takes_largest():
    photos = [SimpleNamespace(file_id="small"), SimpleNamespace(file_id="large")]
    msg = normalize_update(_update(photo=photos))
    assert msg.attachment.kind == "photo"
    assert msg.attachment.file_id == "large"
    assert msg.text is None


def test_normalize_video():
    video = SimpleNamespace(file_id="vid1", file_name="clip.mp4")
    msg = normalize_update(_update(video=video))
    assert msg.attachment.kind == "video"
    assert msg.attachment.file_id == "vid1"
    assert msg.attachment.file_name == "clip.mp4"


def test_normalize_document():
    doc = SimpleNamespace(file_id="doc1", file_name="id.pdf")
    msg = normalize_update(_update(document=doc))
    assert msg.attachment.kind == "document"
    assert msg.attachment.file_id == "doc1"
    assert msg.attachment.file_name == "id.pdf"


def test_normalize_button_tap_becomes_text_value():
    # A tapped button arrives as a callback_query; we surface its data as text.
    msg = normalize_update(_update(callback="consent_yes"))
    assert msg == IncomingMessage(user_id="42", text="consent_yes", attachment=None)


def test_normalize_returns_none_for_empty_update():
    empty = SimpleNamespace(message=None, callback_query=None)
    assert normalize_update(empty) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/channels/test_telegram.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kyc_bot.channels.telegram'`.

- [ ] **Step 3: Write minimal implementation**

```python
# kyc_bot/channels/telegram.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/channels/test_telegram.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add kyc_bot/channels/telegram.py tests/channels/test_telegram.py
git commit -m "feat: normalize Telegram updates into channel-neutral messages"
```

---

### Task 5: TelegramChannel — outbound send + download

**Files:**
- Modify: `kyc_bot/channels/telegram.py` (add the `TelegramChannel` class)
- Test: `tests/channels/test_telegram_channel.py`

This task wraps a PTB `Bot` for outbound calls. The `Bot` is injected (not constructed from a token) so tests pass an `AsyncMock`.

- [ ] **Step 1: Write the failing test**

```python
# tests/channels/test_telegram_channel.py
from types import SimpleNamespace
from unittest.mock import AsyncMock

from kyc_bot.channels.base import Attachment, MessagingChannel, PromptButton
from kyc_bot.channels.telegram import TelegramChannel


def _bot():
    bot = AsyncMock()
    return bot


async def test_is_a_messaging_channel():
    ch = TelegramChannel(bot=_bot())
    assert isinstance(ch, MessagingChannel)


async def test_send_text_calls_bot():
    bot = _bot()
    ch = TelegramChannel(bot=bot)
    await ch.send_text("42", "hello")
    bot.send_message.assert_awaited_once_with(chat_id=42, text="hello")


async def test_send_prompt_builds_inline_keyboard():
    bot = _bot()
    ch = TelegramChannel(bot=bot)
    await ch.send_prompt("42", "Agree?", [PromptButton("Yes", "y"), PromptButton("No", "n")])
    kwargs = bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == 42
    assert kwargs["text"] == "Agree?"
    keyboard = kwargs["reply_markup"].inline_keyboard
    # one row, two buttons, callback_data preserved
    assert [b.text for b in keyboard[0]] == ["Yes", "No"]
    assert [b.callback_data for b in keyboard[0]] == ["y", "n"]


async def test_download_fetches_file_bytes():
    bot = _bot()
    tg_file = SimpleNamespace(download_as_bytearray=AsyncMock(return_value=bytearray(b"IDIMG")))
    bot.get_file = AsyncMock(return_value=tg_file)
    ch = TelegramChannel(bot=bot)
    data = await ch.download(Attachment(kind="photo", file_id="fid9"))
    bot.get_file.assert_awaited_once_with("fid9")
    assert data == b"IDIMG"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/channels/test_telegram_channel.py -v`
Expected: FAIL with `ImportError: cannot import name 'TelegramChannel'`.

- [ ] **Step 3: Add the `TelegramChannel` class to `kyc_bot/channels/telegram.py`**

Add these imports at the top (merge with the existing `from __future__` and typing imports):

```python
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from kyc_bot.channels.base import MessagingChannel, PromptButton
```

Append the class to the end of the file:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/channels/test_telegram_channel.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run the full suite + lint**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check kyc_bot tests`
Expected: 19 passed; ruff reports "All checks passed!".

- [ ] **Step 6: Commit**

```bash
git add kyc_bot/channels/telegram.py tests/channels/test_telegram_channel.py
git commit -m "feat: add TelegramChannel outbound send and file download"
```

---

### Task 6: Runnable bot entrypoint (manual smoke, not auto-tested)

**Files:**
- Create: `kyc_bot/channels/telegram_app.py`
- Modify: `README.md` (append a "Run the Telegram channel" section)

This wires a real long-polling bot that echoes what it receives — proof the channel works end-to-end against real Telegram. It reads the token from `TELEGRAM_BOT_TOKEN` env var (never hard-coded). Not unit-tested (it needs a live token); it is a manual smoke test.

- [ ] **Step 1: Create `kyc_bot/channels/telegram_app.py`**

```python
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
```

- [ ] **Step 2: Verify it imports without a token (should not crash on import)**

Run: `.venv/bin/python -c "import kyc_bot.channels.telegram_app"`
Expected: no output, exit 0 (import must not require the token; only `main()` reads it).

- [ ] **Step 3: Lint**

Run: `.venv/bin/ruff check kyc_bot`
Expected: "All checks passed!"

- [ ] **Step 4: Append run instructions to `README.md`**

Add this section to the end of `README.md`:

```markdown
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
```

- [ ] **Step 5: Manual smoke test (optional, needs a real token)**

Run: `TELEGRAM_BOT_TOKEN=<token> .venv/bin/python -m kyc_bot.channels.telegram_app`
Expected: bot responds in Telegram to `/start`, button taps, and file uploads. Ctrl-C to stop.

- [ ] **Step 6: Commit**

```bash
git add kyc_bot/channels/telegram_app.py README.md
git commit -m "feat: add Telegram echo smoke-test entrypoint and run docs"
```

---

## Definition of Done

- `MessagingChannel` interface exists with `send_text`, `send_prompt`, `download`.
- `TelegramChannel` implements it over `python-telegram-bot`; inbound updates
  (text, photo, video, document, button taps) normalize into `IncomingMessage`.
- 19 unit tests pass with no live token/network; `ruff` is clean.
- A real echo bot runs via `python -m kyc_bot.channels.telegram_app`.
- No KYC flow, verification, or storage introduced (deferred to later plans).
