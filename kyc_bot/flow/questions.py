"""The census questionnaire, defined as data.

Editing the survey = editing the `CENSUS` list. The flow engine walks it
generically over any MessagingChannel, so no engine changes are needed to add,
remove, or reorder questions. Keep it neutral: religion / caste live in the real
census schedule but are intentionally left out of this demo.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

QType = Literal[
    "consent",       # agree / decline gate (must be first)
    "text",          # free text
    "number",        # digits only
    "choice",        # one tappable option
    "multichoice",   # tap several, then Done
    "photo_ocr",     # upload a card photo -> OCR -> masked + name-consistency confirm
    "webapp",        # launch the liveness Mini App (camera), then Continue
]


@dataclass(frozen=True)
class Question:
    """One survey step. `field` is the logical target on CensusRecord; the engine
    maps it by `id`, so keep ids stable."""

    id: str
    prompt: str
    qtype: QType
    field: str
    options: Optional[list[str]] = None


# Linear household + head-of-household survey. (Per-member repetition is a
# documented extension; see docs/census-flow.md.)
CENSUS: list[Question] = [
    Question(
        "consent",
        "🧾 This is a demo census survey. We store your answers only for this demo, "
        "mask any ID number, and never verify against a real government database. "
        "Do you agree to continue?",
        "consent",
        "consent",
    ),
    Question("house_count", "How many people live in this house?", "number", "household.size"),
    Question(
        "ownership",
        "Is the house owned or rented?",
        "choice",
        "household.ownership",
        ["Owned", "Rented", "Other"],
    ),
    Question(
        "assets",
        "Which of these does the household own? Tap all that apply, then Done.",
        "multichoice",
        "household.assets",
        ["Bicycle", "Two-wheeler", "Car", "TV", "Smartphone", "Computer"],
    ),
    Question("name", "Full name of the head of the household?", "text", "head.name"),
    Question(
        "marital",
        "Marital status of the head?",
        "choice",
        "head.marital",
        ["Never married", "Married", "Widowed", "Divorced/Separated"],
    ),
    Question("age", "Age of the head (in years)?", "number", "head.age"),
    Question("sex", "Sex of the head?", "choice", "head.sex", ["Male", "Female", "Other"]),
    Question(
        "id_card",
        "📷 Please upload a photo of the head's Aadhaar or Voter ID card. "
        "(Demo: use a sample/your own card — the number is masked to the last 4 digits.)",
        "photo_ocr",
        "head.id",
    ),
    Question(
        "liveness",
        "Last step: a quick liveness check to confirm a real person was surveyed.",
        "webapp",
        "head.liveness",
    ),
]
