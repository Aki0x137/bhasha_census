"""Channel abstraction: platform-neutral messaging interface and types.

Nothing above the channel layer should import platform SDK types (e.g.
python-telegram-bot). Channels normalize platform events into these
dataclasses and accept these dataclasses when sending.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional

AttachmentKind = Literal["photo", "video", "document"]


@dataclass(frozen=True)
class Attachment:
    """A media file the user sent. `file_id` is a channel-scoped handle used
    to download the bytes later via MessagingChannel.download."""
    kind: AttachmentKind
    file_id: str
    file_name: Optional[str] = None


@dataclass(frozen=True)
class IncomingMessage:
    """A normalized inbound message. Exactly one of text/attachment is the
    meaningful payload for a given message, but both fields always exist."""
    user_id: str
    text: Optional[str] = None
    attachment: Optional[Attachment] = None


@dataclass(frozen=True)
class PromptButton:
    """A tappable choice. `label` is shown to the user; `value` is the stable
    token the flow matches on when the user taps it."""
    label: str
    value: str
