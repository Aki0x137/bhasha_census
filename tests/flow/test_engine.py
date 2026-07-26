from kyc_bot.flow.actions import SendButtons, SendText, SendWebApp
from kyc_bot.flow.engine import OcrAnswer, QuestionnaireEngine
from kyc_bot.flow.session import Session

E = QuestionnaireEngine()


def _new() -> Session:
    return Session(user_id="u1")


def _drive_to_id(s: Session) -> None:
    """Advance a fresh session up to (but not through) the id_card step."""
    E.submit(s, text="__yes__")          # consent
    E.submit(s, text="4")                # house_count
    E.submit(s, text="Owned")            # ownership
    E.submit(s, text="Car")              # assets: toggle
    E.submit(s, text="__done__")         # assets: done
    E.submit(s, text="Ramesh Kumar")     # name
    E.submit(s, text="Married")          # marital
    E.submit(s, text="45")               # age
    E.submit(s, text="Male")             # sex


def test_happy_path_produces_complete_record():
    s = _new()
    _drive_to_id(s)
    # matching card name -> no confirmation needed
    E.submit(s, ocr=OcrAnswer(masked_id="•••• •••• 7777", ocr_name="Ramesh Kumar", name_match=1.0))
    final = E.submit(s, text="__continue__")   # liveness

    r = s.record
    assert r.consent is True
    assert r.household.size == 4
    assert r.household.ownership == "Owned"
    assert r.household.assets == ["Car"]
    assert r.head.name == "Ramesh Kumar"
    assert r.head.marital == "Married"
    assert r.head.age == 45
    assert r.head.sex == "Male"
    assert r.head.id_masked.endswith("7777")
    assert r.head.id_confirmed is True
    assert E.current(s) is None
    assert isinstance(final[0], SendText)
    assert "complete" in final[0].text.lower()


def test_number_validation_rejects_non_digits():
    s = _new()
    E.submit(s, text="__yes__")
    before = s.idx
    out = E.submit(s, text="abc")
    assert s.idx == before                     # did not advance
    assert isinstance(out[0], SendText)


def test_consent_decline_cancels():
    s = _new()
    out = E.submit(s, text="__no__")
    assert s.declined is True
    assert E.current(s) is None
    assert "cancel" in out[0].text.lower()


def test_multichoice_toggles_then_done():
    s = _new()
    E.submit(s, text="__yes__")
    E.submit(s, text="4")
    E.submit(s, text="Owned")
    E.submit(s, text="Car")
    E.submit(s, text="TV")
    E.submit(s, text="Car")                    # toggle Car off
    E.submit(s, text="__done__")
    assert s.record.household.assets == ["TV"]


def test_name_mismatch_asks_for_confirmation():
    s = _new()
    _drive_to_id(s)
    idx_at_id = s.idx
    out = E.submit(s, ocr=OcrAnswer(masked_id="•••• •••• 1234", ocr_name="Suresh Patel",
                                    name_match=0.2))
    assert isinstance(out[0], SendButtons)      # confirm prompt
    assert s.awaiting_confirm is True
    assert s.idx == idx_at_id                    # not advanced yet
    assert s.record.needs_review() is True

    E.submit(s, text="__yes__")                  # human confirms same person
    assert s.record.head.id_confirmed is True
    assert isinstance(E.next_actions(s)[0], SendWebApp)   # advanced to liveness
