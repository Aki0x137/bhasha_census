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


class MessagingChannel(ABC):
    """Everything the KYC flow needs from a chat platform.

    Inbound messages are delivered by the concrete channel (e.g. via a
    handler registered on the platform SDK) as normalized IncomingMessage
    objects; how they reach the flow is the channel's concern. The methods
    below are what the flow calls outbound. A concrete channel must implement
    all three."""

    @abstractmethod
    async def send_text(self, user_id: str, text: str) -> None:
        """Send a plain text message to the user."""

    @abstractmethod
    async def send_prompt(
        self, user_id: str, text: str, buttons: list[PromptButton]
    ) -> None:
        """Send `text` with a set of tappable buttons. When the user taps
        one, the channel delivers an IncomingMessage whose `text` equals the
        chosen button's `value`."""

    @abstractmethod
    async def download(self, attachment: Attachment) -> bytes:
        """Fetch the raw bytes for a previously received attachment."""
