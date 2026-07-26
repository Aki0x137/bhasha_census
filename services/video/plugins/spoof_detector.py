"""Spoof detector plugin — lightweight heuristic (screen reflection, texture uniformity)."""
from __future__ import annotations

import time
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult


class SpoofDetectorPlugin:
    name = "spoof_detector"
    version = "0.1.0"
    capabilities = ["face", "anti_spoof"]

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()
        try:
            import cv2
            import numpy as np

            spoof_scores: list[float] = []
            for frame_path in frames:
                img = cv2.imread(str(frame_path))
                if img is None:
                    continue
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # High-frequency texture check: real faces have more texture variance
                laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                texture_score = float(laplacian.var())
                # Very flat textures (printed photos, screens) have low variance
                # Normalize: if < 50 → suspect, if > 300 → likely real
                suspicion = max(0.0, 1.0 - min(texture_score / 300.0, 1.0))
                spoof_scores.append(suspicion)

            avg_spoof = (sum(spoof_scores) / len(spoof_scores)) if spoof_scores else 0.0
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=True,
                scores={"spoof_score": round(avg_spoof, 3)},
                labels=["spoof_suspect"] if avg_spoof >= 0.7 else ["spoof_ok"],
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
    register_plugin(SpoofDetectorPlugin())
