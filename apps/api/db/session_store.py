"""SQLite session repository.

One active enrollment session allowed per user_ref (FR-013).
Uses stdlib sqlite3; no extra ORM dep for MVP.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from shared.schemas.session import EnrollmentSession
from shared.schemas.common import SessionStatus
from shared.utils.logging import get_logger

logger = get_logger(__name__)

DB_PATH = Path("data/sessions.db")
SESSION_TTL_MS = 24 * 60 * 60 * 1000  # 24 hours


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_ref   TEXT NOT NULL,
                data       TEXT NOT NULL,
                status     TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_ref ON sessions(user_ref)"
        )
        conn.commit()


def _now_ms() -> int:
    return int(time.time() * 1000)


def create_session(session: EnrollmentSession) -> EnrollmentSession:
    now = _now_ms()
    session.created_at_ms = now
    session.updated_at_ms = now
    session.expires_at_ms = now + SESSION_TTL_MS
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,?,?,?)",
            (
                session.session_id,
                session.user_ref,
                session.model_dump_json(),
                session.status.value,
                now,
                now,
                session.expires_at_ms,
            ),
        )
        conn.commit()
    logger.info("session_created", session_id=session.session_id, user_ref=session.user_ref)
    return session


def get_session(session_id: str) -> Optional[EnrollmentSession]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if not row:
        return None
    return EnrollmentSession.model_validate_json(row["data"])


def get_active_session_for_user(user_ref: str) -> Optional[EnrollmentSession]:
    """Return the single active (non-completed/expired) session for a user."""
    active_statuses = [
        s.value for s in SessionStatus
        if s not in (SessionStatus.COMPLETED, SessionStatus.EXPIRED, SessionStatus.FAILED)
    ]
    placeholders = ",".join("?" * len(active_statuses))
    with _connect() as conn:
        row = conn.execute(
            f"SELECT data FROM sessions WHERE user_ref = ? AND status IN ({placeholders}) "
            "ORDER BY created_at DESC LIMIT 1",
            (user_ref, *active_statuses),
        ).fetchone()
    if not row:
        return None
    return EnrollmentSession.model_validate_json(row["data"])


def update_session(session: EnrollmentSession) -> EnrollmentSession:
    session.updated_at_ms = _now_ms()
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET data=?, status=?, updated_at=? WHERE session_id=?",
            (
                session.model_dump_json(),
                session.status.value,
                session.updated_at_ms,
                session.session_id,
            ),
        )
        conn.commit()
    return session


def expire_abandoned_sessions() -> int:
    """Mark sessions past their expires_at as EXPIRED (T072 — 24h policy)."""
    now = _now_ms()
    active_statuses = [
        s.value for s in SessionStatus
        if s not in (SessionStatus.COMPLETED, SessionStatus.EXPIRED, SessionStatus.FAILED)
    ]
    placeholders = ",".join("?" * len(active_statuses))
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT session_id, data FROM sessions WHERE status IN ({placeholders}) AND expires_at < ?",
            (*active_statuses, now),
        ).fetchall()
        count = 0
        for row in rows:
            sess = EnrollmentSession.model_validate_json(row["data"])
            sess.status = SessionStatus.EXPIRED
            sess.updated_at_ms = now
            conn.execute(
                "UPDATE sessions SET data=?, status=?, updated_at=? WHERE session_id=?",
                (sess.model_dump_json(), sess.status.value, now, row["session_id"]),
            )
            count += 1
        conn.commit()
    if count:
        logger.info("sessions_expired", count=count)
    return count
