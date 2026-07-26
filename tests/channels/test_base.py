import pytest

from kyc_bot.channels.base import (
    Attachment,
    IncomingMessage,
    MessagingChannel,
    PromptButton,
)


class FakeChannel(MessagingChannel):
    def __init__(self):
        self.sent_texts: list[tuple[str, str]] = []
        self.sent_prompts: list[tuple[str, str, list[PromptButton]]] = []
        self.files: dict[str, bytes] = {}

    async def send_text(self, user_id: str, text: str) -> None:
        self.sent_texts.append((user_id, text))

    async def send_prompt(self, user_id: str, text: str, buttons: list[PromptButton]) -> None:
        self.sent_prompts.append((user_id, text, buttons))

    async def download(self, attachment: Attachment) -> bytes:
        return self.files[attachment.file_id]


async def test_fake_channel_send_text():
    ch = FakeChannel()
    await ch.send_text("42", "hi")
    assert ch.sent_texts == [("42", "hi")]


async def test_fake_channel_send_prompt():
    ch = FakeChannel()
    btns = [PromptButton("Yes", "y"), PromptButton("No", "n")]
    await ch.send_prompt("42", "Agree?", btns)
    assert ch.sent_prompts == [("42", "Agree?", btns)]


async def test_fake_channel_download():
    ch = FakeChannel()
    ch.files["fid1"] = b"\x89PNG"
    data = await ch.download(Attachment(kind="photo", file_id="fid1"))
    assert data == b"\x89PNG"


def test_cannot_instantiate_incomplete_subclass():
    class Broken(MessagingChannel):
        async def send_text(self, user_id: str, text: str) -> None:
            ...
        # missing send_prompt and download

    with pytest.raises(TypeError):
        Broken()


def test_incoming_message_is_reexported():
    assert IncomingMessage(user_id="1").user_id == "1"
