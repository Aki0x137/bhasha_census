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
