from types import SimpleNamespace

from kyc_bot.channels.base import IncomingMessage
from kyc_bot.channels.telegram import normalize_update


def _update(user_id=42, text=None, photo=None, video=None, document=None, callback=None):
    """Build a minimal object shaped like a PTB Update for normalize_update."""
    message = None
    if text is not None or photo or video or document:
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=user_id),
            text=text,
            photo=photo or [],       # PTB gives a list of PhotoSize; last is largest
            video=video,
            document=document,
        )
    callback_query = None
    if callback is not None:
        callback_query = SimpleNamespace(
            from_user=SimpleNamespace(id=user_id),
            data=callback,
        )
    return SimpleNamespace(message=message, callback_query=callback_query)


def test_normalize_text_message():
    msg = normalize_update(_update(text="hello"))
    assert msg == IncomingMessage(user_id="42", text="hello", attachment=None)


def test_normalize_photo_takes_largest():
    photos = [SimpleNamespace(file_id="small"), SimpleNamespace(file_id="large")]
    msg = normalize_update(_update(photo=photos))
    assert msg.attachment.kind == "photo"
    assert msg.attachment.file_id == "large"
    assert msg.text is None


def test_normalize_video():
    video = SimpleNamespace(file_id="vid1", file_name="clip.mp4")
    msg = normalize_update(_update(video=video))
    assert msg.attachment.kind == "video"
    assert msg.attachment.file_id == "vid1"
    assert msg.attachment.file_name == "clip.mp4"


def test_normalize_document():
    doc = SimpleNamespace(file_id="doc1", file_name="id.pdf")
    msg = normalize_update(_update(document=doc))
    assert msg.attachment.kind == "document"
    assert msg.attachment.file_id == "doc1"
    assert msg.attachment.file_name == "id.pdf"


def test_normalize_button_tap_becomes_text_value():
    msg = normalize_update(_update(callback="consent_yes"))
    assert msg == IncomingMessage(user_id="42", text="consent_yes", attachment=None)


def test_normalize_returns_none_for_empty_update():
    empty = SimpleNamespace(message=None, callback_query=None)
    assert normalize_update(empty) is None
