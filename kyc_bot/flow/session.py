"""Per-user survey session + a simple in-memory store.

In-memory is enough for the MVP/demo; the store interface (get_or_create / reset
/ save) is the seam to swap in SQLite later without touching the engine or bot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from kyc_bot.flow.record import CensusRecord


@dataclass
class Session:
    user_id: str
    idx: int = 0                              # index into CENSUS
    record: CensusRecord = field(default_factory=CensusRecord)
    multi_buffer: list[str] = field(default_factory=list)
    awaiting_confirm: bool = False            # inside the id-card name-confirm sub-step
    declined: bool = False
    saved: bool = False                       # record persisted to SQLite (once, on completion)
    webapp_url: Optional[str] = None          # https URL of the liveness Mini App


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, user_id: str, webapp_url: Optional[str] = None) -> Session:
        s = self._sessions.get(user_id)
        if s is None:
            s = Session(user_id=user_id, webapp_url=webapp_url)
            self._sessions[user_id] = s
        return s

    def reset(self, user_id: str, webapp_url: Optional[str] = None) -> Session:
        s = Session(user_id=user_id, webapp_url=webapp_url)
        self._sessions[user_id] = s
        return s

    def save(self, session: Session) -> None:
        self._sessions[session.user_id] = session
