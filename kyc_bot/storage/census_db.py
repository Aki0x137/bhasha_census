"""SQLite persistence for completed census records + admin approval status.

Self-contained (stdlib sqlite3, no extra deps). The census bot writes records
here on survey completion; the admin web page reads them and updates status.
Records store only the privacy-safe fields — the ID number is already masked
before it reaches here.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from kyc_bot.flow.record import CensusRecord

_STATUSES = ("pending", "approved", "rejected")


def _db_path() -> str:
    # Read at call time so tests / config can override CENSUS_DB_PATH.
    return os.getenv("CENSUS_DB_PATH", "data/census.db")


def _conn() -> sqlite3.Connection:
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS census_records (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at     TEXT NOT NULL,
                user_id        TEXT,
                household_size INTEGER,
                ownership      TEXT,
                assets         TEXT,
                head_name      TEXT,
                head_age       INTEGER,
                head_sex       TEXT,
                head_marital   TEXT,
                id_masked      TEXT,
                id_name        TEXT,
                id_name_match  REAL,
                liveness       TEXT,
                needs_review   INTEGER DEFAULT 0,
                status         TEXT NOT NULL DEFAULT 'pending'
            )
            """
        )


def insert_record(record: CensusRecord, user_id: str = "") -> int:
    h, p = record.household, record.head
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO census_records (
                created_at, user_id, household_size, ownership, assets,
                head_name, head_age, head_sex, head_marital,
                id_masked, id_name, id_name_match, liveness, needs_review, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'pending')
            """,
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                user_id,
                h.size,
                h.ownership,
                json.dumps(h.assets),
                p.name,
                p.age,
                p.sex,
                p.marital,
                p.id_masked,
                p.id_name,
                p.id_name_match,
                p.liveness,
                int(record.needs_review()),
            ),
        )
        return int(cur.lastrowid)


def list_records(status: str | None = None) -> list[dict]:
    query = "SELECT * FROM census_records"
    args: tuple = ()
    if status:
        query += " WHERE status = ?"
        args = (status,)
    query += " ORDER BY id DESC"
    with _conn() as c:
        rows = c.execute(query, args).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["assets"] = json.loads(d["assets"] or "[]")
        out.append(d)
    return out


def counts() -> dict[str, int]:
    with _conn() as c:
        rows = c.execute(
            "SELECT status, COUNT(*) n FROM census_records GROUP BY status"
        ).fetchall()
    result = {s: 0 for s in _STATUSES}
    for r in rows:
        result[r["status"]] = r["n"]
    return result


def set_status(record_id: int, status: str) -> bool:
    if status not in _STATUSES:
        raise ValueError(f"invalid status: {status}")
    with _conn() as c:
        cur = c.execute(
            "UPDATE census_records SET status = ? WHERE id = ?", (status, record_id)
        )
        return cur.rowcount > 0
