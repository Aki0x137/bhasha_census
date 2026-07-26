"""Face tracker plugin — stability across multiple frames."""
from __future__ import annotations

import time
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult
from services.video.mediapipe_compat import count_faces_in_bgr


class FaceTrackerPlugin:
    name = "face_tracker"
    version = "0.1.0"
    capabilities = ["face"]

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()
        try:
            import cv2

            if len(frames) < 2:
                return PluginResult(
                    plugin_name=self.name, plugin_version=self.version, ok=True,
                    scores={"track_stable": True},
                    labels=["single_frame"],
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )

            face_counts: list[int] = []
            for frame_path in frames:
                img = cv2.imread(str(frame_path))
                if img is None:
                    continue
                face_counts.append(count_faces_in_bgr(img))

            stable = all(c == 1 for c in face_counts) if face_counts else False
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=True,
                scores={"track_stable": stable},
                labels=["track_stable"] if stable else ["track_unstable"],
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
    register_plugin(FaceTrackerPlugin())
