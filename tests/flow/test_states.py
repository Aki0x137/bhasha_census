from kyc_bot.flow.states import State, Session


def test_state_members_exist():
    assert {s.name for s in State} >= {
        "GREETING", "MENU", "ASK_NAME", "ASK_EPIC", "ASK_DOB",
        "ASK_ADDRESS", "ASK_PHOTO", "DONE",
    }


def test_session_defaults():
    s = Session(user_id="42")
    assert s.user_id == "42"
    assert s.state is State.GREETING
    assert s.fields == {}


def test_session_can_record_fields_and_advance():
    s = Session(user_id="42")
    s.fields["name"] = "Ravi"
    s.state = State.ASK_EPIC
    assert s.fields["name"] == "Ravi"
    assert s.state is State.ASK_EPIC
