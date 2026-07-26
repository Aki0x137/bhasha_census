from kyc_bot.channels.base import Attachment, IncomingMessage, MessagingChannel, PromptButton
from kyc_bot.flow.session_store import InMemorySessionStore
from kyc_bot.flow.states import State
from kyc_bot.flow.sir_flow import SirFlow, MENU_BUTTON_VALUE


class FakeChannel(MessagingChannel):
    def __init__(self):
        self.texts: list[tuple[str, str]] = []
        self.prompts: list[tuple[str, str, list[PromptButton]]] = []
        self.files: dict[str, bytes] = {}

    async def send_text(self, user_id, text):
        self.texts.append((user_id, text))

    async def send_prompt(self, user_id, text, buttons):
        self.prompts.append((user_id, text, buttons))

    async def download(self, attachment):
        return self.files[attachment.file_id]


class FakeVault:
    def __init__(self):
        self.stored: dict[str, bytes] = {}

    def store(self, name, data):
        path = f"/vault/{name}.enc"
        self.stored[path] = data
        return path


class FakeStore:
    def __init__(self):
        self.saved = []

    def save(self, sub):
        self.saved.append(sub)


def _flow(channel):
    return SirFlow(
        channel=channel,
        sessions=InMemorySessionStore(),
        vault=FakeVault(),
        submissions=FakeStore(),
        ref_factory=lambda: "REF999",
        now=lambda: "2026-07-26T10:00:00",
    )


def _text(user_id, text):
    return IncomingMessage(user_id=user_id, text=text)


def _photo(user_id, file_id):
    return IncomingMessage(user_id=user_id, attachment=Attachment(kind="photo", file_id=file_id))


async def test_start_greets_and_shows_menu():
    ch = FakeChannel()
    flow = _flow(ch)
    await flow.handle(_text("42", "/start"))
    assert len(ch.prompts) == 1
    user_id, text, buttons = ch.prompts[0]
    assert user_id == "42"
    assert "welcome" in text.lower()
    assert buttons[0].value == MENU_BUTTON_VALUE


async def test_menu_tap_asks_for_name():
    ch = FakeChannel()
    flow = _flow(ch)
    await flow.handle(_text("42", "/start"))
    await flow.handle(_text("42", MENU_BUTTON_VALUE))
    assert "name" in ch.texts[-1][1].lower()


async def test_full_happy_path_saves_submission():
    ch = FakeChannel()
    ch.files["photo1"] = b"EPIC-IMAGE-BYTES"
    store = FakeStore()
    vault = FakeVault()
    sessions = InMemorySessionStore()
    flow = SirFlow(
        channel=ch, sessions=sessions, vault=vault, submissions=store,
        ref_factory=lambda: "REF999", now=lambda: "2026-07-26T10:00:00",
    )
    await flow.handle(_text("42", "/start"))
    await flow.handle(_text("42", MENU_BUTTON_VALUE))
    await flow.handle(_text("42", "Ravi Kumar"))     # name
    await flow.handle(_text("42", "ABC1234567"))     # epic
    await flow.handle(_text("42", "1990-01-01"))     # dob
    await flow.handle(_text("42", "12 MG Road"))     # address
    await flow.handle(_photo("42", "photo1"))        # photo -> save

    assert len(store.saved) == 1
    sub = store.saved[0]
    assert sub.id == "REF999"
    assert sub.user_id == "42"
    assert sub.name == "Ravi Kumar"
    assert sub.epic == "ABC1234567"
    assert sub.dob == "1990-01-01"
    assert sub.address == "12 MG Road"
    assert sub.created_at == "2026-07-26T10:00:00"
    assert vault.stored[sub.image_path] == b"EPIC-IMAGE-BYTES"
    assert any("REF999" in t for _, t in ch.texts)
    assert sessions.get_or_create("42").state is State.DONE


async def test_non_photo_at_photo_step_reprompts():
    ch = FakeChannel()
    flow = _flow(ch)
    for m in ["/start", MENU_BUTTON_VALUE, "Ravi", "EPIC1", "1990", "Addr"]:
        await flow.handle(_text("42", m))
    ch.texts.clear()
    await flow.handle(_text("42", "not a photo"))
    assert "photo" in ch.texts[-1][1].lower()


async def test_start_after_done_restarts():
    ch = FakeChannel()
    ch.files["p"] = b"img"
    flow = _flow(ch)
    for m in ["/start", MENU_BUTTON_VALUE, "n", "e", "d", "a"]:
        await flow.handle(_text("42", m))
    await flow.handle(_photo("42", "p"))
    before = len(ch.prompts)
    await flow.handle(_text("42", "/start"))
    assert len(ch.prompts) == before + 1
