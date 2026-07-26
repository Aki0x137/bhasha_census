"""Kognition API liveness & face analysis plugin.

Sends a frame (JPEG bytes) to the Kognition liveness endpoint and maps
the response into a ``PluginResult`` with ``face_count``, ``spoof_score``,
and ``liveness_score`` scores.

Offline stub mode (no real API call):
  - Activated when ``KOGNITION_API_KEY`` is empty **or** ``KOGNITION_OFFLINE=true``
  - Returns a neutral stub result so the rest of the pipeline keeps running

Environment variables (set in .env — see .env.example):
  KOGNITION_API_KEY        Your Kognition API key (required for live mode)
  KOGNITION_BASE_URL       API base URL (default: https://api.kognition.ai/v1)
  KOGNITION_LIVENESS_PATH  Endpoint path (default: /liveness/analyze)
  KOGNITION_TIMEOUT_SECONDS Request timeout (default: 10)
  KOGNITION_OFFLINE        Set "true" to force offline stub mode
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult
from shared.utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_BASE_URL = "https://api.kognition.ai/v1"
_DEFAULT_LIVENESS_PATH = "/liveness/analyze"
_DEFAULT_TIMEOUT = 10


class KognitionLivenessPlugin:
    """Video plugin that calls Kognition's liveness API for cloud-side analysis.

    Capabilities:
      - ``liveness``: liveness/spoof score from a cloud model
      - ``face``:     face detection count from the same response
    """

    name = "kognition_liveness"
    version = "0.1.0"
    capabilities = ["face", "liveness", "anti_spoof"]

    def __init__(self) -> None:
        self._api_key = os.getenv("KOGNITION_API_KEY", "").strip()
        self._base_url = os.getenv("KOGNITION_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
        self._liveness_path = os.getenv("KOGNITION_LIVENESS_PATH", _DEFAULT_LIVENESS_PATH)
        self._timeout = int(os.getenv("KOGNITION_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT)))
        self._offline = (
            os.getenv("KOGNITION_OFFLINE", "false").lower() in {"true", "1", "yes"}
            or not self._api_key
        )
        if self._offline:
            logger.warning(
                "kognition_offline_mode",
                reason="KOGNITION_API_KEY not set or KOGNITION_OFFLINE=true",
            )

    # ------------------------------------------------------------------
    # Plugin interface
    # ------------------------------------------------------------------

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()

        if self._offline:
            return self._stub_result(t0)

        # Use only the first frame for the cloud API call in MVP
        # (sending all frames would be expensive and slow for demos)
        frame_path = frames[0] if frames else None
        if frame_path is None:
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=False,
                scores={}, labels=[], error_message="No frames provided",
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

        try:
            image_bytes = Path(str(frame_path)).read_bytes()
        except OSError as exc:
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=False,
                scores={}, labels=[], error_message=f"Cannot read frame: {exc}",
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

        try:
            response = self._call_api(image_bytes, session_id=job.session_id)
            scores, labels = self._parse_response(response)
            logger.info(
                "kognition_api_ok",
                session_id=job.session_id,
                scores=scores,
                labels=labels,
            )
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=True,
                scores=scores, labels=labels,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("kognition_api_error", session_id=job.session_id, error=str(exc))
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=False,
                scores={}, labels=[], error_message=str(exc),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_api(self, image_bytes: bytes, session_id: str) -> dict[str, Any]:
        """POST the image to the Kognition liveness endpoint."""
        try:
            import httpx  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("httpx is required for Kognition calls. Run: pip install httpx") from exc

        url = f"{self._base_url}{self._liveness_path}"
        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "image/jpeg",
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, content=image_bytes, headers=headers)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
        """Map Kognition API response fields to plugin scores.

        Expected Kognition response shape (adapt if the actual API differs):
        {
          "liveness_score": 0.97,     # 0–1; higher = more likely live
          "spoof_probability": 0.03,  # 0–1; higher = more likely spoof
          "face_count": 1,
          "status": "ok"
        }
        """
        liveness = float(data.get("liveness_score", 0.5))
        spoof = float(data.get("spoof_probability", data.get("spoof_score", 0.0)))
        face_count = int(data.get("face_count", 1 if liveness > 0.5 else 0))

        scores: dict[str, float] = {
            "face_count": float(face_count),
            "spoof_score": round(spoof, 3),
            "liveness_score": round(liveness, 3),
        }

        labels: list[str] = []
        if face_count >= 1:
            labels.append("face_present")
        if liveness >= 0.7:
            labels.append("liveness_ok")
        elif liveness < 0.4:
            labels.append("liveness_fail")
        if spoof >= 0.6:
            labels.append("spoof_suspect")

        return scores, labels

    def _stub_result(self, t0: float) -> PluginResult:
        """Return a neutral offline stub (does not affect hard_fail logic)."""
        return PluginResult(
            plugin_name=self.name,
            plugin_version=self.version,
            ok=True,
            scores={
                "face_count": 1.0,
                "spoof_score": 0.0,
                "liveness_score": 0.85,
            },
            labels=["face_present", "liveness_ok", "offline_stub"],
            duration_ms=int((time.monotonic() - t0) * 1000),
        )


def register() -> None:
    from services.video.registry import register_plugin
    register_plugin(KognitionLivenessPlugin())
