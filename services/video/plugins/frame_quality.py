"""Frame quality scoring plugin — blur, brightness, and resolution checks."""
from __future__ import annotations

import time
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult


class FrameQualityPlugin:
    name = "frame_quality"
    version = "0.1.0"
    capabilities = ["quality"]

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()
        try:
            import cv2
            import numpy as np

            quality_scores: list[float] = []
            for frame_path in frames:
                img = cv2.imread(str(frame_path))
                if img is None:
                    continue
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # Laplacian variance as sharpness proxy
                laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                sharpness = min(laplacian_var / 500.0, 1.0)
                # Brightness
                mean_brightness = float(np.mean(gray)) / 255.0
                brightness_ok = 0.2 <= mean_brightness <= 0.85
                # Resolution check (min 100x100)
                h, w = img.shape[:2]
                res_ok = h >= 100 and w >= 100
                score = sharpness * (0.9 if brightness_ok else 0.4) * (1.0 if res_ok else 0.5)
                quality_scores.append(score)

            avg_quality = (sum(quality_scores) / len(quality_scores)) if quality_scores else 0.0
            return PluginResult(
                plugin_name=self.name,
                plugin_version=self.version,
                ok=True,
                scores={"quality_score": round(avg_quality, 3)},
                labels=["quality_ok"] if avg_quality >= 0.5 else ["quality_low"],
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as exc:
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=False,
                scores={}, labels=[], error_message=str(exc),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )


def register():
    from services.video.registry import register_plugin
    register_plugin(FrameQualityPlugin())
