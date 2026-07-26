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
