"""Outbound actions the engine emits. The channel adapter renders them, so the
engine stays pure (no I/O, easy to unit-test)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class SendText:
    text: str


@dataclass(frozen=True)
class SendButtons:
    text: str
    buttons: list[tuple[str, str]]   # (label, value)


@dataclass(frozen=True)
class RequestPhoto:
    text: str


@dataclass(frozen=True)
class SendWebApp:
    text: str
    label: str
    url: Optional[str]   # None -> adapter shows a Continue fallback


Action = Union[SendText, SendButtons, RequestPhoto, SendWebApp]
