"""Sarvam STT client adapter with fake/offline mode.

In offline/fake mode (SARVAM_API_KEY not set) returns a passthrough
transcript for testing without external network calls.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

from shared.utils.logging import get_logger

logger = get_logger(__name__)

_SARVAM_API_BASE = "https://api.sarvam.ai"
_SARVAM_STT_PATH = "/speech-to-text"


class SarvamSTTClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.fake_mode = not bool(self.api_key)
        if self.fake_mode:
            logger.warning("sarvam_stt_fake_mode", reason="SARVAM_API_KEY not set")

    def transcribe(self, audio_path: str | Path, language_code: str = "en-IN") -> dict:
        """Transcribe audio file. Returns dict with transcript, confidence, latency_ms."""
        t0 = time.monotonic()
        if self.fake_mode:
            transcript = Path(audio_path).stem.replace("_", " ")
            return {
                "transcript": f"[FAKE] {transcript}",
                "confidence": 0.85,
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "request_id": "fake-0000",
            }

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        headers = {"api-subscription-key": self.api_key}
        files = {"file": (Path(audio_path).name, audio_bytes, "audio/ogg")}
        data = {"language_code": language_code, "model": "saarika:v2"}

        try:
            resp = httpx.post(
                f"{_SARVAM_API_BASE}{_SARVAM_STT_PATH}",
                headers=headers,
                files=files,
                data=data,
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
            return {
                "transcript": body.get("transcript", ""),
                "confidence": body.get("confidence", 0.0),
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "request_id": resp.headers.get("x-request-id", ""),
            }
        except httpx.HTTPStatusError as exc:
            logger.error("sarvam_stt_error", status=exc.response.status_code)
            raise
        except Exception as exc:
            logger.error("sarvam_stt_exception", error=str(exc))
            raise


_default_client: SarvamSTTClient | None = None


def get_stt_client() -> SarvamSTTClient:
    global _default_client
    if _default_client is None:
        _default_client = SarvamSTTClient()
    return _default_client
