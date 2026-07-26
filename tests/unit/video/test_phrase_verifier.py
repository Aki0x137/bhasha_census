"""Unit tests for speech phrase verifier (no network — uses fake STT)."""
from __future__ import annotations

import os
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def no_sarvam_key(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)


def test_verify_phrase_fake_mode(tmp_path):
    pytest.importorskip("httpx")
    from services.speech.phrase_verifier import verify_phrase

    audio = tmp_path / "test_voice.ogg"
    audio.write_bytes(b"\x00" * 16)

    evidence = verify_phrase(
        audio_path=audio,
        session_id="sess_test",
        challenge_id="c1",
        expected_phrase="census enrollment",
    )
    assert evidence.session_id == "sess_test"
    assert evidence.challenge_id == "c1"
    assert isinstance(evidence.phrase_match_score, float)
    assert 0.0 <= evidence.phrase_match_score <= 1.0


def test_field_matcher_name_match():
    from services.document.field_matcher import _name_match
    assert _name_match("Test User", "Test User") == 1.0
    assert _name_match("test user extra words", "Test User") == 1.0
    assert _name_match("completely different", "Test User") < 0.5


def test_field_matcher_dob_exact():
    from services.document.field_matcher import _dob_match
    assert _dob_match("19900101", "19900101") == 1.0
    assert _dob_match("1990-01-01", "19900101") == 1.0
    assert _dob_match("19850501", "19900101") == 0.0
