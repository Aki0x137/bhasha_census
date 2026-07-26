"""Document-verification provider interface + result type.

A provider takes raw image bytes and returns extracted fields. The default
implementation is a Fake (offline); a Sarvam Doc-AI implementation drops in
behind the same interface. Nothing above this layer sees a full ID number.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OcrResult:
    """Raw extraction from a document. `id_number` is the full number as read;
    it is masked immediately by the caller and never persisted in full."""

    name: str
    id_number: str
    quality: float = 1.0


class DocProvider(Protocol):
    async def digitize(self, image: bytes) -> OcrResult: ...
