# SIR Registration Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Telegram conversation that registers a user for the ECI SIR (electoral-roll revision): greeting → menu → collect 4 elector fields → EPIC photo upload → persist encrypted → success message.

**Architecture:** Builds on the existing channel layer (`kyc_bot/channels/`, unchanged). A platform-agnostic `SirFlow` state machine advances a per-user `Session` on each inbound `IncomingMessage`, calling `MessagingChannel` to send prompts. On photo upload it downloads bytes via the channel, encrypts and stores the image in a Fernet file vault, and writes the 4 PII fields (encrypted) to SQLite. Live session is in-memory; only the completed submission is persisted.

**Tech Stack:** Python 3.12 (venv at `.venv`), `cryptography` (Fernet), stdlib `sqlite3`, existing `python-telegram-bot`, `pytest` + `pytest-asyncio`.

**Base branch:** `feat/sir-registration-flow` off `main` (channel layer already merged). Do NOT modify anything under `kyc_bot/channels/`.

---

### Task 1: Add cryptography dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Add `cryptography` to `pyproject.toml` dependencies**

In `pyproject.toml`, change the `dependencies` list under `[project]` from:

```toml
dependencies = [
    "python-telegram-bot==21.6",
]
```
to:
```toml
dependencies = [
    "python-telegram-bot==21.6",
    "cryptography==43.0.1",
]
```

- [ ] **Step 2: Add it to `requirements.txt`**

Add this line after the `python-telegram-bot==21.6` line:
```
cryptography==43.0.1
```

- [ ] **Step 3: Install**

Run: `cd /Users/psabata/bhasaha_census && .venv/bin/pip install -e ".[dev]"`
Expected: installs `cryptography` (and its `cffi` dep) with no errors.

- [ ] **Step 4: Verify import**

Run: `.venv/bin/python -c "from cryptography.fernet import Fernet; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements.txt
git commit -m "chore: add cryptography dependency for encrypted storage"
```

---

### Task 2: Crypto helpers

**Files:**
- Create: `kyc_bot/storage/__init__.py` (empty)
- Create: `kyc_bot/storage/crypto.py`
- Test: `tests/storage/__init__.py` (empty)
- Test: `tests/storage/test_crypto.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_crypto.py
import pytest
from cryptography.fernet import Fernet

from kyc_bot.storage import crypto


def test_encrypt_decrypt_bytes_roundtrip():
    key = Fernet.generate_key()
    token = crypto.encrypt(b"secret bytes", key)
    assert token != b"secret bytes"
    assert crypto.decrypt(token, key) == b"secret bytes"


def test_encrypt_decrypt_str_roundtrip():
    key = Fernet.generate_key()
    token = crypto.encrypt_str("Ravi Kumar", key)
    assert isinstance(token, str)
    assert token != "Ravi Kumar"
    assert crypto.decrypt_str(token, key) == "Ravi Kumar"


def test_load_key_reads_env(monkeypatch):
    k = Fernet.generate_key().decode()
    monkeypatch.setenv("KYC_MASTER_KEY", k)
    assert crypto.load_key() == k.encode()


def test_load_key_missing_raises(monkeypatch):
    monkeypatch.delenv("KYC_MASTER_KEY", raising=False)
    with pytest.raises(RuntimeError, match="KYC_MASTER_KEY"):
        crypto.load_key()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/storage/test_crypto.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kyc_bot.storage'`.

- [ ] **Step 3: Create the package markers and implementation**

Create `kyc_bot/storage/__init__.py` (empty) and `tests/storage/__init__.py` (empty).

Create `kyc_bot/storage/crypto.py`:

```python
"""Symmetric encryption helpers (Fernet) for at-rest PII and image storage.

The key is a urlsafe-base64 Fernet key supplied via the KYC_MASTER_KEY env var.
For MVP a single symmetric key is used; a later slice can move this to a KMS.
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet


def load_key() -> bytes:
    """Return the Fernet key from KYC_MASTER_KEY, or raise if unset."""
    key = os.environ.get("KYC_MASTER_KEY")
    if not key:
        raise RuntimeError(
            "KYC_MASTER_KEY env var is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"`"
        )
    return key.encode()


def encrypt(data: bytes, key: bytes) -> bytes:
    """Encrypt raw bytes, returning a Fernet token (bytes)."""
    return Fernet(key).encrypt(data)


def decrypt(token: bytes, key: bytes) -> bytes:
    """Decrypt a Fernet token back to raw bytes."""
    return Fernet(key).decrypt(token)


def encrypt_str(text: str, key: bytes) -> str:
    """Encrypt a string, returning a str token (utf-8 decoded)."""
    return encrypt(text.encode("utf-8"), key).decode("utf-8")


def decrypt_str(token: str, key: bytes) -> str:
    """Decrypt a str token back to the original string."""
    return decrypt(token.encode("utf-8"), key).decode("utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/storage/test_crypto.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add kyc_bot/storage/__init__.py kyc_bot/storage/crypto.py tests/storage/__init__.py tests/storage/test_crypto.py
git commit -m "feat: add Fernet crypto helpers for at-rest encryption"
```

---

### Task 3: Encrypted file vault

**Files:**
- Create: `kyc_bot/storage/vault.py`
- Test: `tests/storage/test_vault.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_vault.py
from cryptography.fernet import Fernet

from kyc_bot.storage.vault import Vault


def test_store_then_load_roundtrips(tmp_path):
    key = Fernet.generate_key()
    vault = Vault(root=tmp_path / "vault", key=key)
    path = vault.store("epic_abc", b"\x89PNG-image-bytes")
    assert vault.load(path) == b"\x89PNG-image-bytes"


def test_stored_file_is_not_plaintext(tmp_path):
    key = Fernet.generate_key()
    vault = Vault(root=tmp_path / "vault", key=key)
    path = vault.store("epic_abc", b"PLAINTEXT-MARKER")
    on_disk = (tmp_path / "vault" / "epic_abc.enc").read_bytes()
    assert b"PLAINTEXT-MARKER" not in on_disk


def test_store_creates_root_dir(tmp_path):
    key = Fernet.generate_key()
    root = tmp_path / "nested" / "vault"
    vault = Vault(root=root, key=key)
    vault.store("x", b"data")
    assert root.is_dir()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/storage/test_vault.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kyc_bot.storage.vault'`.

- [ ] **Step 3: Write minimal implementation**

```python
# kyc_bot/storage/vault.py
"""Encrypted file vault: writes Fernet-encrypted blobs to disk."""
from __future__ import annotations

from pathlib import Path

from kyc_bot.storage import crypto


class Vault:
    """Stores encrypted files under `root`. Each blob is written as
    `<root>/<name>.enc` containing the Fernet ciphertext of the data."""

    def __init__(self, root: Path, key: bytes):
        self._root = Path(root)
        self._key = key

    def store(self, name: str, data: bytes) -> str:
        """Encrypt `data` and write it to `<root>/<name>.enc`. Returns the path."""
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._root / f"{name}.enc"
        path.write_bytes(crypto.encrypt(data, self._key))
        return str(path)

    def load(self, path: str) -> bytes:
        """Read and decrypt a previously stored file."""
        return crypto.decrypt(Path(path).read_bytes(), self._key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/storage/test_vault.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add kyc_bot/storage/vault.py tests/storage/test_vault.py
git commit -m "feat: add encrypted file vault for image storage"
```

---

### Task 4: SQLite submission store

**Files:**
- Create: `kyc_bot/storage/db.py`
- Test: `tests/storage/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_db.py
from cryptography.fernet import Fernet

from kyc_bot.storage.db import Submission, SubmissionStore


def _sub(id="ref123"):
    return Submission(
        id=id,
        user_id="42",
        name="Ravi Kumar",
        epic="ABC1234567",
        dob="1990-01-01",
        address="12 MG Road, Bengaluru",
        image_path="/tmp/vault/epic_ref123.enc",
        created_at="2026-07-26T10:00:00",
    )


def test_save_then_get_roundtrip(tmp_path):
    key = Fernet.generate_key()
    store = SubmissionStore(tmp_path / "s.db", key=key)
    store.save(_sub())
    got = store.get("ref123")
    assert got == _sub()


def test_pii_columns_are_ciphertext_on_disk(tmp_path):
    import sqlite3

    key = Fernet.generate_key()
    db_path = tmp_path / "s.db"
    store = SubmissionStore(db_path, key=key)
    store.save(_sub())
    raw = sqlite3.connect(db_path).execute(
        "SELECT name_enc, epic_enc, dob_enc, address_enc FROM submissions"
    ).fetchone()
    for col in raw:
        assert "Ravi Kumar" not in col
        assert "ABC1234567" not in col


def test_get_unknown_returns_none(tmp_path):
    key = Fernet.generate_key()
    store = SubmissionStore(tmp_path / "s.db", key=key)
    assert store.get("nope") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/storage/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kyc_bot.storage.db'`.

- [ ] **Step 3: Write minimal implementation**

```python
# kyc_bot/storage/db.py
"""SQLite store for completed SIR submissions. PII fields are encrypted."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from kyc_bot.storage import crypto

_SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name_enc TEXT NOT NULL,
    epic_enc TEXT NOT NULL,
    dob_enc TEXT NOT NULL,
    address_enc TEXT NOT NULL,
    image_path TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class Submission:
    id: str
    user_id: str
    name: str
    epic: str
    dob: str
    address: str
    image_path: str
    created_at: str


class SubmissionStore:
    """Persists Submissions to SQLite with the four PII fields encrypted."""

    def __init__(self, db_path: Path, key: bytes):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._key = key
        with sqlite3.connect(self._path) as conn:
            conn.execute(_SCHEMA)

    def save(self, sub: Submission) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                "INSERT INTO submissions "
                "(id, user_id, name_enc, epic_enc, dob_enc, address_enc, "
                "image_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sub.id,
                    sub.user_id,
                    crypto.encrypt_str(sub.name, self._key),
                    crypto.encrypt_str(sub.epic, self._key),
                    crypto.encrypt_str(sub.dob, self._key),
                    crypto.encrypt_str(sub.address, self._key),
                    sub.image_path,
                    sub.created_at,
                ),
            )

    def get(self, submission_id: str) -> Optional[Submission]:
        with sqlite3.connect(self._path) as conn:
            row = conn.execute(
                "SELECT id, user_id, name_enc, epic_enc, dob_enc, address_enc, "
                "image_path, created_at FROM submissions WHERE id = ?",
                (submission_id,),
            ).fetchone()
        if row is None:
            return None
        return Submission(
            id=row[0],
            user_id=row[1],
            name=crypto.decrypt_str(row[2], self._key),
            epic=crypto.decrypt_str(row[3], self._key),
            dob=crypto.decrypt_str(row[4], self._key),
            address=crypto.decrypt_str(row[5], self._key),
            image_path=row[6],
            created_at=row[7],
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/storage/test_db.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add kyc_bot/storage/db.py tests/storage/test_db.py
git commit -m "feat: add SQLite submission store with encrypted PII"
```

---

### Task 5: Flow states & session

**Files:**
- Create: `kyc_bot/flow/__init__.py` (empty)
- Create: `kyc_bot/flow/states.py`
- Test: `tests/flow/__init__.py` (empty)
- Test: `tests/flow/test_states.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/flow/test_states.py
from kyc_bot.flow.states import State, Session


def test_state_members_exist():
    assert {s.name for s in State} >= {
        "GREETING", "MENU", "ASK_NAME", "ASK_EPIC", "ASK_DOB",
        "ASK_ADDRESS", "ASK_PHOTO", "DONE",
    }


def test_session_defaults():
    s = Session(user_id="42")
    assert s.user_id == "42"
    assert s.state is State.GREETING
    assert s.fields == {}


def test_session_can_record_fields_and_advance():
    s = Session(user_id="42")
    s.fields["name"] = "Ravi"
    s.state = State.ASK_EPIC
    assert s.fields["name"] == "Ravi"
    assert s.state is State.ASK_EPIC
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/flow/test_states.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kyc_bot.flow'`.

- [ ] **Step 3: Write minimal implementation**

Create `kyc_bot/flow/__init__.py` (empty) and `tests/flow/__init__.py` (empty).

Create `kyc_bot/flow/states.py`:

```python
"""Conversation states and per-user session for the SIR registration flow."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class State(Enum):
    GREETING = auto()
    MENU = auto()
    ASK_NAME = auto()
    ASK_EPIC = auto()
    ASK_DOB = auto()
    ASK_ADDRESS = auto()
    ASK_PHOTO = auto()
    DONE = auto()


@dataclass
class Session:
    """Live, in-memory conversation state for one user."""
    user_id: str
    state: State = State.GREETING
    fields: dict[str, str] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/flow/test_states.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add kyc_bot/flow/__init__.py kyc_bot/flow/states.py tests/flow/__init__.py tests/flow/test_states.py
git commit -m "feat: add SIR flow states and session model"
```

---

### Task 6: In-memory session store

**Files:**
- Create: `kyc_bot/flow/session_store.py`
- Test: `tests/flow/test_session_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/flow/test_session_store.py
from kyc_bot.flow.session_store import InMemorySessionStore
from kyc_bot.flow.states import State


def test_get_or_create_creates_new():
    store = InMemorySessionStore()
    s = store.get_or_create("42")
    assert s.user_id == "42"
    assert s.state is State.GREETING


def test_get_or_create_returns_same_instance():
    store = InMemorySessionStore()
    a = store.get_or_create("42")
    a.state = State.ASK_NAME
    b = store.get_or_create("42")
    assert b is a
    assert b.state is State.ASK_NAME


def test_reset_clears_session():
    store = InMemorySessionStore()
    a = store.get_or_create("42")
    a.state = State.ASK_EPIC
    store.reset("42")
    b = store.get_or_create("42")
    assert b.state is State.GREETING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/flow/test_session_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kyc_bot.flow.session_store'`.

- [ ] **Step 3: Write minimal implementation**

```python
# kyc_bot/flow/session_store.py
"""In-memory store of live conversation sessions, keyed by user id."""
from __future__ import annotations

from kyc_bot.flow.states import Session


class InMemorySessionStore:
    """Holds one Session per user for the lifetime of the process."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, user_id: str) -> Session:
        if user_id not in self._sessions:
            self._sessions[user_id] = Session(user_id=user_id)
        return self._sessions[user_id]

    def reset(self, user_id: str) -> None:
        """Drop any existing session so the next get_or_create starts fresh."""
        self._sessions.pop(user_id, None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/flow/test_session_store.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add kyc_bot/flow/session_store.py tests/flow/test_session_store.py
git commit -m "feat: add in-memory session store"
```

---

### Task 7: SirFlow state machine

**Files:**
- Create: `kyc_bot/flow/sir_flow.py`
- Test: `tests/flow/test_sir_flow.py`

This is the core. `SirFlow.handle(msg)` advances the session and drives the channel. It takes a `MessagingChannel`, a session store, a `Vault`, a `SubmissionStore`, and two injected callables for non-determinism: `ref_factory()` (returns the submission id string) and `now()` (returns the ISO timestamp string) — injected so tests are deterministic.

- [ ] **Step 1: Write the failing test**

```python
# tests/flow/test_sir_flow.py
import pytest

from kyc_bot.channels.base import Attachment, IncomingMessage, MessagingChannel, PromptButton
from kyc_bot.flow.session_store import InMemorySessionStore
from kyc_bot.flow.states import State
from kyc_bot.flow.sir_flow import SirFlow, MENU_BUTTON_VALUE


class FakeChannel(MessagingChannel):
    def __init__(self):
        self.texts: list[tuple[str, str]] = []
        self.prompts: list[tuple[str, str, list[PromptButton]]] = []
        self.files: dict[str, bytes] = {}

    async def send_text(self, user_id, text):
        self.texts.append((user_id, text))

    async def send_prompt(self, user_id, text, buttons):
        self.prompts.append((user_id, text, buttons))

    async def download(self, attachment):
        return self.files[attachment.file_id]


class FakeVault:
    def __init__(self):
        self.stored: dict[str, bytes] = {}

    def store(self, name, data):
        path = f"/vault/{name}.enc"
        self.stored[path] = data
        return path


class FakeStore:
    def __init__(self):
        self.saved = []

    def save(self, sub):
        self.saved.append(sub)


def _flow(channel):
    return SirFlow(
        channel=channel,
        sessions=InMemorySessionStore(),
        vault=FakeVault(),
        submissions=FakeStore(),
        ref_factory=lambda: "REF999",
        now=lambda: "2026-07-26T10:00:00",
    )


def _text(user_id, text):
    return IncomingMessage(user_id=user_id, text=text)


def _photo(user_id, file_id):
    return IncomingMessage(user_id=user_id, attachment=Attachment(kind="photo", file_id=file_id))


async def test_start_greets_and_shows_menu():
    ch = FakeChannel()
    flow = _flow(ch)
    await flow.handle(_text("42", "/start"))
    assert len(ch.prompts) == 1
    user_id, text, buttons = ch.prompts[0]
    assert user_id == "42"
    assert "welcome" in text.lower()
    assert buttons[0].value == MENU_BUTTON_VALUE


async def test_menu_tap_asks_for_name():
    ch = FakeChannel()
    flow = _flow(ch)
    await flow.handle(_text("42", "/start"))
    await flow.handle(_text("42", MENU_BUTTON_VALUE))
    assert "name" in ch.texts[-1][1].lower()


async def test_full_happy_path_saves_submission():
    ch = FakeChannel()
    ch.files["photo1"] = b"EPIC-IMAGE-BYTES"
    store = FakeStore()
    vault = FakeVault()
    sessions = InMemorySessionStore()
    flow = SirFlow(
        channel=ch, sessions=sessions, vault=vault, submissions=store,
        ref_factory=lambda: "REF999", now=lambda: "2026-07-26T10:00:00",
    )
    await flow.handle(_text("42", "/start"))
    await flow.handle(_text("42", MENU_BUTTON_VALUE))
    await flow.handle(_text("42", "Ravi Kumar"))     # name
    await flow.handle(_text("42", "ABC1234567"))     # epic
    await flow.handle(_text("42", "1990-01-01"))     # dob
    await flow.handle(_text("42", "12 MG Road"))     # address
    await flow.handle(_photo("42", "photo1"))        # photo -> save

    assert len(store.saved) == 1
    sub = store.saved[0]
    assert sub.id == "REF999"
    assert sub.user_id == "42"
    assert sub.name == "Ravi Kumar"
    assert sub.epic == "ABC1234567"
    assert sub.dob == "1990-01-01"
    assert sub.address == "12 MG Road"
    assert sub.created_at == "2026-07-26T10:00:00"
    # image bytes were stored in the vault, path recorded on the submission
    assert vault.stored[sub.image_path] == b"EPIC-IMAGE-BYTES"
    # success message with the ref was sent
    assert any("REF999" in t for _, t in ch.texts)
    # session ended
    assert sessions.get_or_create("42").state is State.DONE


async def test_non_photo_at_photo_step_reprompts():
    ch = FakeChannel()
    flow = _flow(ch)
    for m in ["/start", MENU_BUTTON_VALUE, "Ravi", "EPIC1", "1990", "Addr"]:
        await flow.handle(_text("42", m))
    ch.texts.clear()
    await flow.handle(_text("42", "not a photo"))
    assert "photo" in ch.texts[-1][1].lower()


async def test_start_after_done_restarts():
    ch = FakeChannel()
    ch.files["p"] = b"img"
    flow = _flow(ch)
    for m in ["/start", MENU_BUTTON_VALUE, "n", "e", "d", "a"]:
        await flow.handle(_text("42", m))
    await flow.handle(_photo("42", "p"))
    # now DONE; /start should greet again with a menu prompt
    before = len(ch.prompts)
    await flow.handle(_text("42", "/start"))
    assert len(ch.prompts) == before + 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/flow/test_sir_flow.py -v`
Expected: FAIL with `ImportError: cannot import name 'SirFlow'`.

- [ ] **Step 3: Write minimal implementation**

```python
# kyc_bot/flow/sir_flow.py
"""SirFlow: platform-agnostic state machine for SIR registration.

Advances an in-memory Session on each inbound IncomingMessage and drives the
MessagingChannel to send prompts. On EPIC photo upload it downloads the bytes,
stores them encrypted in the vault, and persists the submission. Non-determinism
(ref id, timestamp) is injected for deterministic tests.
"""
from __future__ import annotations

from typing import Callable

from kyc_bot.channels.base import IncomingMessage, MessagingChannel, PromptButton
from kyc_bot.flow.session_store import InMemorySessionStore
from kyc_bot.flow.states import Session, State
from kyc_bot.storage.db import Submission

MENU_BUTTON_VALUE = "register_sir"

_GREETING = "👋 Welcome to the SIR registration bot for the electoral roll."
_ASK = {
    "name": "What is your full name?",
    "epic": "What is your EPIC (voter ID) number?",
    "dob": "What is your date of birth?",
    "address": "What is your address?",
}
_ASK_PHOTO = "Please upload a photo of your EPIC / voter ID card."

# (state we are IN when the user's text arrives) -> (field to store, next state, next prompt key)
_TEXT_STEPS = {
    State.ASK_NAME: ("name", State.ASK_EPIC, "epic"),
    State.ASK_EPIC: ("epic", State.ASK_DOB, "dob"),
    State.ASK_DOB: ("dob", State.ASK_ADDRESS, "address"),
    State.ASK_ADDRESS: ("address", State.ASK_PHOTO, None),  # None -> ask for photo
}


class SirFlow:
    def __init__(
        self,
        channel: MessagingChannel,
        sessions: InMemorySessionStore,
        vault,
        submissions,
        ref_factory: Callable[[], str],
        now: Callable[[], str],
    ):
        self._channel = channel
        self._sessions = sessions
        self._vault = vault
        self._submissions = submissions
        self._ref_factory = ref_factory
        self._now = now

    async def handle(self, msg: IncomingMessage) -> None:
        user_id = msg.user_id

        # /start always (re)starts the journey.
        if msg.text == "/start":
            self._sessions.reset(user_id)
            session = self._sessions.get_or_create(user_id)
            session.state = State.MENU
            await self._channel.send_prompt(
                user_id,
                f"{_GREETING}\n\nTap below to begin:",
                [PromptButton("Register for SIR", MENU_BUTTON_VALUE)],
            )
            return

        session = self._sessions.get_or_create(user_id)

        if session.state is State.MENU and msg.text == MENU_BUTTON_VALUE:
            session.state = State.ASK_NAME
            await self._channel.send_text(user_id, _ASK["name"])
            return

        if session.state in _TEXT_STEPS and msg.text is not None:
            field, next_state, prompt_key = _TEXT_STEPS[session.state]
            session.fields[field] = msg.text
            session.state = next_state
            if prompt_key is not None:
                await self._channel.send_text(user_id, _ASK[prompt_key])
            else:
                await self._channel.send_text(user_id, _ASK_PHOTO)
            return

        if session.state is State.ASK_PHOTO:
            if msg.attachment is None or msg.attachment.kind != "photo":
                await self._channel.send_text(user_id, _ASK_PHOTO)
                return
            await self._save(session, msg)
            return

        # Any other message before /start: nudge the user to start.
        await self._channel.send_text(user_id, "Send /start to begin.")

    async def _save(self, session: Session, msg: IncomingMessage) -> None:
        ref = self._ref_factory()
        data = await self._channel.download(msg.attachment)
        image_path = self._vault.store(f"epic_{ref}", data)
        submission = Submission(
            id=ref,
            user_id=session.user_id,
            name=session.fields.get("name", ""),
            epic=session.fields.get("epic", ""),
            dob=session.fields.get("dob", ""),
            address=session.fields.get("address", ""),
            image_path=image_path,
            created_at=self._now(),
        )
        self._submissions.save(submission)
        session.state = State.DONE
        await self._channel.send_text(
            session.user_id, f"✅ Submission received! Ref: {ref}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/flow/test_sir_flow.py -v`
Expected: 6 passed.

- [ ] **Step 5: Run full suite + lint**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check kyc_bot tests`
Expected: all pass (19 channel + 4 crypto + 3 vault + 3 db + 3 states + 3 session + 6 flow = 41); ruff clean.

- [ ] **Step 6: Commit**

```bash
git add kyc_bot/flow/sir_flow.py tests/flow/test_sir_flow.py
git commit -m "feat: add SirFlow registration state machine"
```

---

### Task 8: Config + real app entrypoint (manual smoke)

**Files:**
- Create: `kyc_bot/config.py`
- Create: `kyc_bot/app.py`
- Modify: `README.md` (append a "Run the SIR bot" section)

Not unit-tested (needs a live token). `app.py` wires everything and runs long-polling.

- [ ] **Step 1: Create `kyc_bot/config.py`**

```python
# kyc_bot/config.py
"""Env-driven configuration for the SIR bot."""
from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Base data directory (holds the vault and the SQLite db)."""
    return Path(os.environ.get("KYC_DATA_DIR", "./data"))


def vault_dir() -> Path:
    return data_dir() / "vault"


def db_path() -> Path:
    return data_dir() / "submissions.db"
```

- [ ] **Step 2: Verify config imports**

Run: `.venv/bin/python -c "from kyc_bot import config; print(config.db_path())"`
Expected: prints `data/submissions.db`.

- [ ] **Step 3: Create `kyc_bot/app.py`**

```python
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
```

- [ ] **Step 4: Verify it imports without env vars (must not read them at import)**

Run: `.venv/bin/python -c "import kyc_bot.app"`
Expected: no output, exit 0.

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check kyc_bot`
Expected: "All checks passed!"

- [ ] **Step 6: Append run instructions to `README.md`**

Append this section to the end of `README.md`:

```markdown
## Run the SIR registration bot

1. Create a bot with @BotFather and copy the token.
2. Generate an encryption key:

   ```bash
   .venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. Run:

   ```bash
   TELEGRAM_BOT_TOKEN=<token> KYC_MASTER_KEY=<key> .venv/bin/python -m kyc_bot.app
   ```

4. In Telegram, send `/start`, tap **Register for SIR**, answer the four
   prompts (name, EPIC number, DOB, address), then upload a photo of your
   EPIC card. The bot replies with a submission reference. Data is stored
   encrypted under `./data` (override with `KYC_DATA_DIR`).
```

- [ ] **Step 7: Full suite (nothing new to test, confirm nothing broke)**

Run: `.venv/bin/pytest -q`
Expected: 41 passed.

- [ ] **Step 8: Commit**

```bash
git add kyc_bot/config.py kyc_bot/app.py README.md
git commit -m "feat: add SIR bot config and runnable entrypoint"
```

---

## Definition of Done

- `/start` greets and shows the "Register for SIR" button.
- The four fields are collected in order, then an EPIC photo is requested.
- On photo upload, the submission is saved (PII encrypted in SQLite, image in
  the Fernet vault) and the user receives "✅ Submission received! Ref: <id>".
- All unit tests pass (channel layer untouched and still green); ruff clean.
- `python -m kyc_bot.app` runs the real bot end-to-end with a live token.
