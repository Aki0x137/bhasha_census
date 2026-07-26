# SIR Registration Flow — Design Spec (Slice 2)

**Date:** 2026-07-26
**Status:** Approved for planning
**Builds on:** the channel layer (`kyc_bot/channels/`) shipped in slice 1.

## 1. Goal

A smooth Telegram conversation that registers a user for the Election
Commission of India's **SIR** (Special Intensive Revision of electoral rolls):
greeting → menu → collect 4 elector fields → EPIC photo upload → persist
(encrypted) → success message.

## 2. Scope

### In scope
- A conversation state machine driving the journey, platform-agnostic (calls
  `MessagingChannel`, never Telegram types directly).
- Greeting + a one-button menu ("Register for SIR").
- Collect four fields (accepted as-is, no validation this slice): full name,
  EPIC number, date of birth, address.
- One image upload: a photo of the EPIC / voter ID card.
- Persist the submission: 4 PII fields encrypted into SQLite, EPIC image into a
  Fernet-encrypted file vault.
- Success message with a reference id.
- Wiring: a real Telegram handler that routes updates through the flow.

### Out of scope (this slice)
- Field validation, `/cancel`, review-and-confirm step (accept-as-is for now).
- Liveness, face-match, OCR (the full-KYC spec's verification — future slices).
- Manual review queue / admin UI.
- Session persistence across bot restart (live session is in-memory).
- Multiple menu options (structure allows adding later; one button now).

## 3. Architecture

Reuses slice 1 unchanged: `MessagingChannel` interface, `TelegramChannel`,
`normalize_update`. New modules sit above (flow) and below (storage) the channel.

```
kyc_bot/
  channels/            # slice 1 — unchanged
  flow/
    states.py          # State enum + Session dataclass + field order
    sir_flow.py        # SirFlow: advances a session per inbound message
    session_store.py   # InMemorySessionStore (user_id -> Session)
  storage/
    vault.py           # Fernet-encrypted file vault for images
    db.py              # SQLite submissions store (PII encrypted)
    crypto.py          # load key from env, encrypt/decrypt helpers
  config.py            # env-driven paths + key loading
  app.py               # real Telegram entrypoint wiring flow + storage
```

## 4. Conversation flow (state machine)

States and transitions:

```
GREETING     -> (on /start) send greeting + menu button; go to MENU
MENU         -> (tap "register_sir") ask name; go to ASK_NAME
ASK_NAME     -> capture text as name; ask EPIC; go to ASK_EPIC
ASK_EPIC     -> capture text as epic; ask DOB; go to ASK_DOB
ASK_DOB      -> capture text as dob; ask address; go to ASK_ADDRESS
ASK_ADDRESS  -> capture text as address; ask for EPIC photo; go to ASK_PHOTO
ASK_PHOTO    -> on photo attachment: download bytes, save submission, reply
                "✅ Submission received! Ref: <id>"; go to DONE
DONE         -> (on /start) restart at GREETING
```

Rules for this slice:
- Text fields are accepted verbatim (no validation).
- In `ASK_PHOTO`, a non-photo message re-prompts "Please upload a photo of your
  EPIC / voter ID card."
- The menu button tap arrives as text equal to its `value` ("register_sir"),
  per the channel contract from slice 1.
- Live session state is held in an in-memory store keyed by `user_id`.

## 5. Storage

### crypto.py
- `load_key()` reads `KYC_MASTER_KEY` from env (a urlsafe base64 Fernet key). If
  unset, raise a clear error naming the env var.
- `encrypt(data: bytes) -> bytes` / `decrypt(token: bytes) -> bytes` using Fernet.
- `encrypt_str(s: str) -> str` / `decrypt_str(token: str) -> str` convenience
  wrappers (utf-8 + base64 text in/out).

### vault.py
- `Vault(root: Path)`: `store(name: str, data: bytes) -> str` writes
  `encrypt(data)` to `root/<name>.enc` and returns the path. `load(path) ->
  bytes` decrypts. The vault dir is created if missing.

### db.py
- SQLite table `submissions`:
  `id TEXT PRIMARY KEY, user_id TEXT, name_enc TEXT, epic_enc TEXT,
   dob_enc TEXT, address_enc TEXT, image_path TEXT, created_at TEXT`.
- `SubmissionStore(db_path)`: `save(Submission) -> None`, `get(id) -> Submission`.
- The four PII fields are stored encrypted (`encrypt_str`); `get` decrypts.
- `id` is a short random hex ref shown to the user. `created_at` is passed in by
  the caller (ISO string) to keep the store deterministic/testable.

## 6. Wiring (app.py)

- Reads `TELEGRAM_BOT_TOKEN`, builds the PTB `Application`, constructs a
  `TelegramChannel`, an `InMemorySessionStore`, a `Vault`, and a
  `SubmissionStore`, and a `SirFlow` binding them.
- One handler routes every update: `normalize_update` -> `SirFlow.handle(msg)`.
- Answers callback queries so button taps don't spin.

## 7. Config
- `KYC_MASTER_KEY` — Fernet key (required to run app.py; tests inject their own).
- `KYC_DATA_DIR` — base dir; defaults to `./data`. Vault at `<dir>/vault`,
  DB at `<dir>/submissions.db`.
- `TELEGRAM_BOT_TOKEN` — bot token (app.py only).

## 8. Testing
- **crypto:** encrypt/decrypt round-trip (bytes + str); missing-key error.
- **vault:** store then load round-trips original bytes; file on disk is not
  plaintext.
- **db:** save then get round-trips a Submission with fields decrypted; on-disk
  columns are ciphertext (not the plaintext values).
- **flow:** a `FakeChannel` (from slice 1 test style) + `FakeVault`/in-memory
  store drive the full journey: /start → menu tap → 4 fields → photo → assert a
  submission was saved and the success ref was sent. Also: non-photo at
  ASK_PHOTO re-prompts; /start at DONE restarts.
- app.py wiring is validated by a manual run (needs a live token), not unit-tested.

## 9. Definition of Done
- `/start` greets and shows the "Register for SIR" button.
- Tapping it walks the user through name/EPIC/DOB/address, then requests the
  EPIC photo.
- On photo upload, the submission is saved (PII encrypted in SQLite, image in
  the encrypted vault) and the user gets "✅ Submission received! Ref: <id>".
- Flow/storage unit tests pass; channel layer remains unchanged and green.
