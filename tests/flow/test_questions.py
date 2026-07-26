from kyc_bot.flow.questions import CENSUS


def test_census_is_non_empty():
    assert len(CENSUS) >= 5


def test_ids_are_unique():
    ids = [q.id for q in CENSUS]
    assert len(ids) == len(set(ids))


def test_consent_is_first():
    assert CENSUS[0].qtype == "consent"


def test_choice_questions_have_options():
    for q in CENSUS:
        if q.qtype in ("choice", "multichoice"):
            assert q.options, f"{q.id} must define options"
