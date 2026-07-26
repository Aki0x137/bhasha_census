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
