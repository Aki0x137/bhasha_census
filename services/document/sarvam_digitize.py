"""Sarvam Document Digitization client with fake/offline mode."""
from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

from shared.utils.logging import get_logger

logger = get_logger(__name__)

_API_BASE = "https://api.sarvam.ai"
_DOC_PATH = "/v1/parse"


class SarvamDocClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.fake_mode = not bool(self.api_key)
        if self.fake_mode:
            logger.warning("sarvam_doc_fake_mode", reason="SARVAM_API_KEY not set")

    def digitize(self, image_path: str | Path) -> dict:
        """Return extracted document text and structured fields."""
        t0 = time.monotonic()
        if self.fake_mode:
            return {
                "document_text": "FAKE DOCUMENT TEXT: Name: Test User, DOB: 1990-01-01",
                "structured_output": {
                    "full_name": "Test User",
                    "date_of_birth": "1990-01-01",
                    "document_type": "ID_CARD",
                },
                "quality_score": 0.9,
                "request_id": "fake-doc-0000",
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }

        headers = {"api-subscription-key": self.api_key}
        with open(image_path, "rb") as f:
            files = {"file": (Path(image_path).name, f.read(), "image/jpeg")}

        try:
            resp = httpx.post(
                f"{_API_BASE}{_DOC_PATH}",
                headers=headers,
                files=files,
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
            return {
                "document_text": body.get("text", ""),
                "structured_output": body.get("fields", {}),
                "quality_score": body.get("confidence", 0.0),
                "request_id": resp.headers.get("x-request-id", ""),
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }
        except httpx.HTTPStatusError as exc:
            logger.error("sarvam_doc_error", status=exc.response.status_code)
            raise
        except Exception as exc:
            logger.error("sarvam_doc_exception", error=str(exc))
            raise


_default_client: SarvamDocClient | None = None


def get_doc_client() -> SarvamDocClient:
    global _default_client
    if _default_client is None:
        _default_client = SarvamDocClient()
    return _default_client
