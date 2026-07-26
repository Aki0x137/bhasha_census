from kyc_bot.channels.base import Attachment, IncomingMessage, PromptButton


def test_attachment_holds_kind_and_file_id():
    att = Attachment(kind="photo", file_id="AgACAgID", file_name=None)
    assert att.kind == "photo"
    assert att.file_id == "AgACAgID"
    assert att.file_name is None


def test_incoming_message_text_only():
    msg = IncomingMessage(user_id="42", text="hello", attachment=None)
    assert msg.user_id == "42"
    assert msg.text == "hello"
    assert msg.attachment is None


def test_incoming_message_with_attachment():
    att = Attachment(kind="video", file_id="BAACAg", file_name="clip.mp4")
    msg = IncomingMessage(user_id="42", text=None, attachment=att)
    assert msg.attachment.kind == "video"
    assert msg.text is None


def test_prompt_button_label_and_value():
    btn = PromptButton(label="I agree", value="consent_yes")
    assert btn.label == "I agree"
    assert btn.value == "consent_yes"
