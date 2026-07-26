"""SirFlow: platform-agnostic state machine for SIR registration.

Advances an in-memory Session on each inbound IncomingMessage and drives the
MessagingChannel to send prompts. On EPIC photo upload it downloads the bytes,
stores them encrypted in the vault, and persists the submission. Non-determinism
(ref id, timestamp) is injected for deterministic tests.
"""
from __future__ import annotations

from typing import Callable

from kyc_bot.channels.base import IncomingMessage, MessagingChannel, PromptButton
from kyc_bot.flow.session_store import InMemorySessionStore
from kyc_bot.flow.states import Session, State
from kyc_bot.storage.db import Submission

MENU_BUTTON_VALUE = "register_sir"

_GREETING = "👋 Welcome to the SIR registration bot for the electoral roll."
_ASK = {
    "name": "What is your full name?",
    "epic": "What is your EPIC (voter ID) number?",
    "dob": "What is your date of birth?",
    "address": "What is your address?",
}
_ASK_PHOTO = "Please upload a photo of your EPIC / voter ID card."

# (state we are IN when text arrives) -> (field to store, next state, next prompt key)
_TEXT_STEPS = {
    State.ASK_NAME: ("name", State.ASK_EPIC, "epic"),
    State.ASK_EPIC: ("epic", State.ASK_DOB, "dob"),
    State.ASK_DOB: ("dob", State.ASK_ADDRESS, "address"),
    State.ASK_ADDRESS: ("address", State.ASK_PHOTO, None),  # None -> ask for photo
}


class SirFlow:
    def __init__(
        self,
        channel: MessagingChannel,
        sessions: InMemorySessionStore,
        vault,
        submissions,
        ref_factory: Callable[[], str],
        now: Callable[[], str],
    ):
        self._channel = channel
        self._sessions = sessions
        self._vault = vault
        self._submissions = submissions
        self._ref_factory = ref_factory
        self._now = now

    async def handle(self, msg: IncomingMessage) -> None:
        user_id = msg.user_id

        if msg.text == "/start":
            self._sessions.reset(user_id)
            session = self._sessions.get_or_create(user_id)
            session.state = State.MENU
            await self._channel.send_prompt(
                user_id,
                f"{_GREETING}\n\nTap below to begin:",
                [PromptButton("Register for SIR", MENU_BUTTON_VALUE)],
            )
            return

        session = self._sessions.get_or_create(user_id)

        if session.state is State.MENU and msg.text == MENU_BUTTON_VALUE:
            session.state = State.ASK_NAME
            await self._channel.send_text(user_id, _ASK["name"])
            return

        if session.state in _TEXT_STEPS and msg.text is not None:
            field, next_state, prompt_key = _TEXT_STEPS[session.state]
            session.fields[field] = msg.text
            session.state = next_state
            if prompt_key is not None:
                await self._channel.send_text(user_id, _ASK[prompt_key])
            else:
                await self._channel.send_text(user_id, _ASK_PHOTO)
            return

        if session.state is State.ASK_PHOTO:
            if msg.attachment is None or msg.attachment.kind != "photo":
                await self._channel.send_text(user_id, _ASK_PHOTO)
                return
            await self._save(session, msg)
            return

        await self._channel.send_text(user_id, "Send /start to begin.")

    async def _save(self, session: Session, msg: IncomingMessage) -> None:
        ref = self._ref_factory()
        data = await self._channel.download(msg.attachment)
        image_path = self._vault.store(f"epic_{ref}", data)
        submission = Submission(
            id=ref,
            user_id=session.user_id,
            name=session.fields.get("name", ""),
            epic=session.fields.get("epic", ""),
            dob=session.fields.get("dob", ""),
            address=session.fields.get("address", ""),
            image_path=image_path,
            created_at=self._now(),
        )
        self._submissions.save(submission)
        session.state = State.DONE
        await self._channel.send_text(
            session.user_id, f"✅ Submission received! Ref: {ref}"
        )
