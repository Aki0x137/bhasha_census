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
        """True when a human should reconcile the record. Surfaced, never used to
        auto-reject. Flags on either: (a) the card name doesn't match the typed
        name (and wasn't confirmed), or (b) the liveness check isn't a clean pass."""
        h = self.head
        name_mismatch = (
            h.id_name_match is not None and h.id_name_match < 0.7 and not h.id_confirmed
        )
        liveness_ok = h.liveness in ("submitted", "passed", "accepted")
        return name_mismatch or not liveness_ok
