"""Sarvam document OCR client with fake/offline mode."""
from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

from shared.utils.logging import get_logger

logger = get_logger(__name__)

_SARVAM_API_BASE = "https://api.sarvam.ai"
_OCR_PATH = "/parse/parse-document"


class SarvamOCRClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.fake_mode = not bool(self.api_key)
        if self.fake_mode:
            logger.warning("sarvam_ocr_fake_mode", reason="SARVAM_API_KEY not set")

    def parse_document(self, image_path: str | Path) -> dict:
        """OCR a document image. Returns detected_fields dict and raw text."""
        t0 = time.monotonic()
        if self.fake_mode:
            name = Path(image_path).stem
            return {
                "document_text": f"[FAKE OCR] Name: Test User DOB: 1990-01-01",
                "detected_fields": {
                    "full_name": "Test User",
                    "date_of_birth": "1990-01-01",
                    "gender": "Male",
                    "id_number": "FAKE123456",
                },
                "document_quality_score": 0.75,
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }

        with open(image_path, "rb") as f:
            img_bytes = f.read()

        headers = {"api-subscription-key": self.api_key}
        files = {"file": (Path(image_path).name, img_bytes, "image/jpeg")}

        try:
            resp = httpx.post(
                f"{_SARVAM_API_BASE}{_OCR_PATH}",
                headers=headers,
                files=files,
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
            return {
                "document_text": body.get("raw_text", ""),
                "detected_fields": body.get("fields", {}),
                "document_quality_score": body.get("quality_score", 0.5),
                "latency_ms": int((time.monotonic() - t0) * 1000),
            }
        except httpx.HTTPStatusError as exc:
            logger.error("sarvam_ocr_error", status=exc.response.status_code)
            raise


_default_client: SarvamOCRClient | None = None


def get_ocr_client() -> SarvamOCRClient:
    global _default_client
    if _default_client is None:
        _default_client = SarvamOCRClient()
    return _default_client
