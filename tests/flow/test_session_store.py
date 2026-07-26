from kyc_bot.flow.session_store import InMemorySessionStore
from kyc_bot.flow.states import State


def test_get_or_create_creates_new():
    store = InMemorySessionStore()
    s = store.get_or_create("42")
    assert s.user_id == "42"
    assert s.state is State.GREETING


def test_get_or_create_returns_same_instance():
    store = InMemorySessionStore()
    a = store.get_or_create("42")
    a.state = State.ASK_NAME
    b = store.get_or_create("42")
    assert b is a
    assert b.state is State.ASK_NAME


def test_reset_clears_session():
    store = InMemorySessionStore()
    a = store.get_or_create("42")
    a.state = State.ASK_EPIC
    store.reset("42")
    b = store.get_or_create("42")
    assert b.state is State.GREETING
