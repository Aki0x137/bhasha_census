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
