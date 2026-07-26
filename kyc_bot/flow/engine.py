"""Questionnaire engine — a pure state machine over the CENSUS list.

No I/O lives here: the channel adapter performs downloads/OCR/webapp and feeds
typed answers in via `submit`. That keeps the whole survey unit-testable with no
Telegram and no network. The adapter loop is:

    render(engine.next_actions(session))     # first prompt after /start
    ...on each user message...
    render(engine.submit(session, text=...)) # validates, advances, returns next prompt(s)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from kyc_bot.flow.actions import Action, RequestPhoto, SendButtons, SendText, SendWebApp
from kyc_bot.flow.questions import CENSUS, Question
from kyc_bot.flow.record import CensusRecord
from kyc_bot.flow.session import Session

NAME_CONFIRM_THRESHOLD = 0.7


@dataclass(frozen=True)
class OcrAnswer:
    """What the adapter hands the engine after reading an uploaded card:
    already masked, already name-matched — the engine never sees the full ID."""

    masked_id: str
    ocr_name: str
    name_match: float


class QuestionnaireEngine:
    # ---- read helpers -------------------------------------------------
    def current(self, session: Session) -> Optional[Question]:
        if session.idx >= len(CENSUS):
            return None
        return CENSUS[session.idx]

    def next_actions(self, session: Session) -> list[Action]:
        q = self.current(session)
        if q is None:
            return [SendText(_summary(session.record))]
        return self._prompt_for(q, session)

    # ---- the one write entry point ------------------------------------
    def submit(
        self,
        session: Session,
        *,
        text: Optional[str] = None,
        ocr: Optional[OcrAnswer] = None,
    ) -> list[Action]:
        q = self.current(session)
        if q is None:
            return [SendText("Survey already complete. Send /start to begin again.")]

        if q.qtype == "consent":
            if text == "__no__":
                session.idx = len(CENSUS)
                session.declined = True
                return [SendText("No problem — the survey was cancelled. Send /start anytime.")]
            if text != "__yes__":
                return self._prompt_for(q, session)
            session.record.consent = True

        elif q.qtype == "text":
            if not text or not text.strip():
                return [SendText("Please type a value.")]
            _store(session, q, text.strip())

        elif q.qtype == "number":
            if not text or not text.strip().isdigit():
                return [SendText("Please send a number (digits only).")]
            _store(session, q, int(text.strip()))

        elif q.qtype == "choice":
            if text not in (q.options or []):
                return self._prompt_for(q, session)
            _store(session, q, text)

        elif q.qtype == "multichoice":
            if text == "__done__":
                _store(session, q, list(session.multi_buffer))
                session.multi_buffer.clear()
            elif text in (q.options or []):
                if text in session.multi_buffer:
                    session.multi_buffer.remove(text)
                else:
                    session.multi_buffer.append(text)
                return self._prompt_for(q, session)   # re-render, do not advance
            else:
                return self._prompt_for(q, session)

        elif q.qtype == "photo_ocr":
            if session.awaiting_confirm:
                session.record.head.id_confirmed = text == "__yes__"
                session.awaiting_confirm = False
                # fall through to advance either way (mismatch stays flagged for review)
            elif ocr is None:
                return [RequestPhoto("Please upload a photo of the ID card.")]
            else:
                head = session.record.head
                head.id_masked = ocr.masked_id
                head.id_name = ocr.ocr_name
                head.id_name_match = ocr.name_match
                if ocr.name_match < NAME_CONFIRM_THRESHOLD:
                    session.awaiting_confirm = True
                    return [
                        SendButtons(
                            f"⚠️ The card name reads “{ocr.ocr_name}”, but you told me "
                            f"“{head.name}”. Is this the same person? "
                            f"(You decide — nothing is auto-rejected.)",
                            [("Yes, same person", "__yes__"), ("No", "__no__")],
                        )
                    ]
                head.id_confirmed = True

        elif q.qtype == "webapp":
            session.record.head.liveness = text or "completed"

        # advance to the next question
        session.idx += 1
        session.awaiting_confirm = False
        nxt = self.current(session)
        if nxt is None:
            return [SendText(_summary(session.record))]
        return self._prompt_for(nxt, session)

    # ---- prompt rendering ---------------------------------------------
    def _prompt_for(self, q: Question, session: Session) -> list[Action]:
        if q.qtype == "consent":
            return [SendButtons(q.prompt, [("I agree", "__yes__"), ("I decline", "__no__")])]
        if q.qtype in ("text", "number"):
            return [SendText(q.prompt)]
        if q.qtype == "choice":
            return [SendButtons(q.prompt, [(o, o) for o in (q.options or [])])]
        if q.qtype == "multichoice":
            selected = ", ".join(session.multi_buffer) or "none yet"
            buttons = [(o, o) for o in (q.options or [])] + [("✅ Done", "__done__")]
            return [SendButtons(f"{q.prompt}\nSelected: {selected}", buttons)]
        if q.qtype == "photo_ocr":
            return [RequestPhoto(q.prompt)]
        if q.qtype == "webapp":
            return [SendWebApp(q.prompt, "📷 Open camera", session.webapp_url)]
        return [SendText(q.prompt)]


# ---- module helpers ---------------------------------------------------
def _store(session: Session, q: Question, value) -> None:
    r = session.record
    if q.id == "house_count":
        r.household.size = value
    elif q.id == "ownership":
        r.household.ownership = value
    elif q.id == "assets":
        r.household.assets = value
    elif q.id == "name":
        r.head.name = value
    elif q.id == "marital":
        r.head.marital = value
    elif q.id == "age":
        r.head.age = value
    elif q.id == "sex":
        r.head.sex = value


def _summary(record: CensusRecord) -> str:
    h = record.household
    p = record.head
    assets = ", ".join(h.assets) if h.assets else "none"
    lines = [
        "✅ *Survey complete.* Recorded:",
        f"• People in house: {h.size if h.size is not None else '—'}",
        f"• Ownership: {h.ownership or '—'}",
        f"• Assets: {assets}",
        f"• Head: {p.name or '—'}, {p.sex or '—'}, age {p.age if p.age is not None else '—'}, "
        f"{p.marital or '—'}",
        f"• ID (masked): {p.id_masked or '—'}  ·  card name: {p.id_name or '—'}",
        f"• Liveness: {p.liveness or '—'}",
    ]
    if record.needs_review():
        lines.append("⚠️ Name mismatch flagged for enumerator review (not rejected).")
    lines.append("\nSend /start to survey another household.")
    return "\n".join(lines)
