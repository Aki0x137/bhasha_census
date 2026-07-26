"""Face detector plugin using MediaPipe Face Detection (OpenCV Haar fallback)."""
from __future__ import annotations

import time
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult
from services.video.mediapipe_compat import count_faces_in_bgr


class FaceDetectorPlugin:
    name = "face_detector"
    version = "0.1.0"
    capabilities = ["face"]

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()
        try:
            import cv2

            face_count = 0
            for frame_path in frames:
                img = cv2.imread(str(frame_path))
                if img is None:
                    continue
                face_count = max(face_count, count_faces_in_bgr(img))

            return PluginResult(
                plugin_name=self.name,
                plugin_version=self.version,
                ok=True,
                scores={"face_count": face_count},
                labels=["single_face"] if face_count == 1 else (["multi_face"] if face_count > 1 else ["no_face"]),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as exc:
            return PluginResult(
                plugin_name=self.name,
                plugin_version=self.version,
                ok=False,
                scores={"face_count": 0},
                labels=[],
                error_message=str(exc),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )


def register():
    from services.video.registry import register_plugin
    register_plugin(FaceDetectorPlugin())
