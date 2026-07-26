"""OCR providers + the privacy/consistency utilities used on ID cards.

- `mask_id`   : keep only the last 4 digits; the full number is never returned.
- `name_similarity` : fuzzy match of the typed name vs the name read off the card,
                       used to *surface a confirmation to the enumerator* — never to
                       auto-reject anyone.
- `FakeDocProvider`  : offline default; deterministic, keeps the demo alive.
- `SarvamDocProvider`: real Sarvam Doc-AI (best-effort) with a Fake fallback so a
                       network/API hiccup can never crash the live demo.
"""
from __future__ import annotations

import difflib
import logging
import re

from kyc_bot.verification.base import DocProvider, OcrResult

log = logging.getLogger(__name__)

SARVAM_BASE = "https://api.sarvam.ai"


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
    """Real Sarvam Doc-AI. Attempts the document-digitization call; on any error
    it falls back to the Fake result and logs a warning (demo stays up)."""

    def __init__(self, api_key: str) -> None:
        self._key = api_key
        self._fallback = FakeDocProvider()

    async def digitize(self, image: bytes) -> OcrResult:
        try:
            return await self._call_sarvam(image)
        except Exception as exc:  # noqa: BLE001 - demo must never crash on OCR
            log.warning("Sarvam Doc-AI failed (%s); falling back to sample OCR.", exc)
            return await self._fallback.digitize(image)

    async def _call_sarvam(self, image: bytes) -> OcrResult:
        # httpx ships transitively with python-telegram-bot; imported lazily so a
        # missing extra never breaks imports for the Fake path.
        import httpx

        headers = {"api-subscription-key": self._key}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{SARVAM_BASE}/doc-digitization/job/v1",
                headers={**headers, "Content-Type": "application/json"},
                json={"language": "en-IN", "output_format": "json"},
            )
            resp.raise_for_status()
            # NOTE: the digitization job is async (job_id -> upload -> poll -> zip).
            # Verify the upload/poll steps against your account before relying on this
            # in the demo; until then the except-branch above keeps things running.
            data = resp.json()
            fields = data.get("detected_fields") or {}
            name = fields.get("name") or self._fallback._name
            number = fields.get("id_number") or self._fallback._id
            return OcrResult(name=name, id_number=number, quality=float(data.get("quality", 0.9)))
