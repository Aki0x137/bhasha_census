"""Typed census record — the artifact the survey produces."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Person:
    name: str = ""
    age: Optional[int] = None
    sex: str = ""
    marital: str = ""
    # ID capture is OCR-only and privacy-preserving: we keep the masked number
    # (last 4) and the name read off the card, never the full ID number.
    id_masked: str = ""
    id_name: str = ""
    id_name_match: Optional[float] = None   # similarity of typed name vs card name [0,1]
    id_confirmed: Optional[bool] = None     # enumerator's human confirmation on a mismatch
    liveness: str = ""


@dataclass
class Household:
    size: Optional[int] = None
    ownership: str = ""
    assets: list[str] = field(default_factory=list)


@dataclass
class CensusRecord:
    consent: bool = False
    household: Household = field(default_factory=Household)
    head: Person = field(default_factory=Person)

    def needs_review(self) -> bool:
        """True when a human should reconcile the record (name mismatch not yet
        confirmed). This is surfaced, never used to auto-reject anyone."""
        h = self.head
        return h.id_name_match is not None and h.id_name_match < 0.7 and not h.id_confirmed
