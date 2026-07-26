"""Temporal anomaly detector — replay/freeze hints for video clips."""
from __future__ import annotations

import time
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult


class TemporalAnomalyDetectorPlugin:
    name = "temporal_anomaly_detector"
    version = "0.1.0"
    capabilities = ["anti_spoof"]

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()
        try:
            import cv2
            import numpy as np

            if len(frames) < 2:
                return PluginResult(
                    plugin_name=self.name, plugin_version=self.version, ok=True,
                    scores={"replay_score": 0.0}, labels=["single_frame"],
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )

            prev_gray = None
            diffs: list[float] = []
            for frame_path in frames:
                img = cv2.imread(str(frame_path))
                if img is None:
                    continue
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(float)
                if prev_gray is not None:
                    diff = float(np.mean(np.abs(gray - prev_gray)))
                    diffs.append(diff)
                prev_gray = gray

            if not diffs:
                replay_score = 0.0
            else:
                avg_diff = sum(diffs) / len(diffs)
                # Very low diff across frames = possible freeze/replay
                replay_score = max(0.0, 1.0 - min(avg_diff / 10.0, 1.0))

            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=True,
                scores={"replay_score": round(replay_score, 3)},
                labels=["replay_suspect"] if replay_score >= 0.7 else ["motion_ok"],
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
    register_plugin(TemporalAnomalyDetectorPlugin())
