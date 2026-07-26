from types import SimpleNamespace
from unittest.mock import AsyncMock

from kyc_bot.channels.base import Attachment, MessagingChannel, PromptButton
from kyc_bot.channels.telegram import TelegramChannel


def _bot():
    bot = AsyncMock()
    return bot


async def test_is_a_messaging_channel():
    ch = TelegramChannel(bot=_bot())
    assert isinstance(ch, MessagingChannel)


async def test_send_text_calls_bot():
    bot = _bot()
    ch = TelegramChannel(bot=bot)
    await ch.send_text("42", "hello")
    bot.send_message.assert_awaited_once_with(chat_id=42, text="hello")


async def test_send_prompt_builds_inline_keyboard():
    bot = _bot()
    ch = TelegramChannel(bot=bot)
    await ch.send_prompt("42", "Agree?", [PromptButton("Yes", "y"), PromptButton("No", "n")])
    kwargs = bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == 42
    assert kwargs["text"] == "Agree?"
    keyboard = kwargs["reply_markup"].inline_keyboard
    assert [b.text for b in keyboard[0]] == ["Yes", "No"]
    assert [b.callback_data for b in keyboard[0]] == ["y", "n"]


async def test_download_fetches_file_bytes():
    bot = _bot()
    tg_file = SimpleNamespace(download_as_bytearray=AsyncMock(return_value=bytearray(b"IDIMG")))
    bot.get_file = AsyncMock(return_value=tg_file)
    ch = TelegramChannel(bot=bot)
    data = await ch.download(Attachment(kind="photo", file_id="fid9"))
    bot.get_file.assert_awaited_once_with("fid9")
    assert data == b"IDIMG"
