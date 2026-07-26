"""OCR providers + the privacy/consistency utilities used on ID cards.

- `mask_id`   : keep only the last 4 digits; the full number is never returned.
- `name_similarity` : fuzzy match of the typed name vs the name read off the card,
                       used to *surface a confirmation to the enumerator* — never to
                       auto-reject anyone.
- `FakeDocProvider`  : offline default; deterministic, keeps the demo alive.
- `SarvamDocProvider`: real Sarvam Doc-AI via the official SDK — actually reads the
                       uploaded card — with a Fake fallback so a network/API hiccup
                       can never crash the live demo.
"""
from __future__ import annotations

import asyncio
import difflib
import logging
import re
import tempfile
import zipfile
from pathlib import Path

from kyc_bot.verification.base import DocProvider, OcrResult

log = logging.getLogger(__name__)


def mask_id(raw: str) -> str:
    """Return a masked ID showing only the last 4 characters. Full number is
    intentionally discarded here so it never reaches storage or logs."""
    digits = re.sub(r"\s+", "", raw or "")
    if len(digits) <= 4:
        return "•••• " + digits
    return "•••• •••• " + digits[-4:]


def name_similarity(a: str, b: str) -> float:
    """Normalized fuzzy similarity in [0, 1]. Case/space/punct-insensitive."""
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()

    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


class FakeDocProvider(DocProvider):
    """Deterministic sample extraction. Uses a neutral sample identity so the
    demo runs with no key and no network."""

    def __init__(self, name: str = "Ramesh Kumar", id_number: str = "999988887777") -> None:
        self._name = name
        self._id = id_number

    async def digitize(self, image: bytes) -> OcrResult:
        return OcrResult(name=self._name, id_number=self._id, quality=0.95)


class SarvamDocProvider(DocProvider):
    """Real Sarvam Doc-AI via the official SDK. Runs the async digitization job
    (create -> upload -> start -> poll -> download markdown) and parses the name +
    ID number off the card. Falls back to the sample on any error/timeout so a live
    demo never crashes."""

    def __init__(self, api_key: str, language: str = "en-IN", timeout: float = 90.0) -> None:
        self._key = api_key
        self._language = language
        self._timeout = timeout
        self._fallback = FakeDocProvider()

    async def digitize(self, image: bytes) -> OcrResult:
        try:
            # SDK calls are blocking; run them off the event loop.
            return await asyncio.to_thread(self._run, image)
        except Exception as exc:  # noqa: BLE001 - demo must never crash on OCR
            log.warning("Sarvam Doc-AI failed (%s); falling back to sample OCR.", exc)
            return await self._fallback.digitize(image)

    def _run(self, image: bytes) -> OcrResult:
        from sarvamai import SarvamAI

        client = SarvamAI(api_subscription_key=self._key)
        with tempfile.TemporaryDirectory() as tmp:
            # Match the file extension to the actual bytes, or Sarvam rejects it
            # as a corrupted image (Telegram sends JPEG; uploads may be PNG).
            suffix = ".png" if image[:4] == b"\x89PNG" else ".jpg"
            img_path = Path(tmp) / f"card{suffix}"
            img_path.write_bytes(image)
            job = client.document_intelligence.create_job(
                language=self._language, output_format="md"
            )
            job.upload_file(str(img_path))
            job.start()
            job.wait_until_complete(poll_interval=2.0, timeout=self._timeout)
            zip_path = Path(tmp) / "out.zip"
            job.download_output(str(zip_path))
            text = ""
            with zipfile.ZipFile(zip_path) as z:
                for name in z.namelist():
                    if name.endswith((".md", ".txt")):
                        text += z.read(name).decode("utf-8", "ignore") + "\n"
        result = _parse_card(text)
        log.info("Sarvam Doc-AI read card: name=%r id=***%s", result.name, result.id_number[-4:])
        return result


def _parse_card(text: str) -> OcrResult:
    """Pull a name and an ID number out of the OCR markdown text."""
    name = ""
    m = re.search(r"(?im)^\s*name\s*[:\-]\s*(.+?)\s*$", text)
    if m:
        name = re.sub(r"\s+", " ", m.group(1)).strip()

    # ID: prefer a long digit run (Aadhaar-style), else fall back to a
    # reference/ID/number-labelled value like "Test Reference: OCR-TEST-4827-1936"
    # so the masked last-4 is meaningful (…1936) instead of the "0000" default.
    number = ""
    for chunk in re.findall(r"\d[\d ]{6,}\d", text):
        digits = re.sub(r"\D", "", chunk)
        if len(digits) > len(number):
            number = digits
    if not number:
        m = re.search(
            r"(?im)(?:reference|ref|number|no|epic|\bid)\b[^\n:]*[:\-]\s*"
            r"([A-Za-z0-9][A-Za-z0-9 /\-]{3,})",
            text,
        )
        if m:
            number = re.sub(r"[^A-Za-z0-9]", "", m.group(1))

    return OcrResult(name=name or "Unknown", id_number=number or "", quality=0.9)
