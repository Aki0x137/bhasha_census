"""Mouth movement detector plugin — weak liveness cue via lip distance."""
from __future__ import annotations

import time
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult

_UPPER_LIP = 13
_LOWER_LIP = 14


class MouthMovementDetectorPlugin:
    name = "mouth_movement_detector"
    version = "0.1.0"
    capabilities = ["liveness_cue"]

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()
        try:
            import cv2
            import mediapipe as mp

            from services.video.mediapipe_compat import has_solutions

            if not has_solutions():
                return PluginResult(
                    plugin_name=self.name, plugin_version=self.version, ok=True,
                    scores={"motion_score": 0.5},
                    labels=["mouth_skipped_no_mediapipe_solutions"],
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )

            if len(frames) < 2:
                return PluginResult(
                    plugin_name=self.name, plugin_version=self.version, ok=True,
                    scores={"motion_score": 0.5}, labels=["single_frame_skip"],
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )

            mp_fm = mp.solutions.face_mesh
            openings: list[float] = []
            for frame_path in frames:
                img = cv2.imread(str(frame_path))
                if img is None:
                    continue
                h, w = img.shape[:2]
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                with mp_fm.FaceMesh(static_image_mode=True) as fm:
                    res = fm.process(img_rgb)
                    if not res.multi_face_landmarks:
                        continue
                    lms = res.multi_face_landmarks[0].landmark
                    opening = abs(lms[_UPPER_LIP].y - lms[_LOWER_LIP].y)
                    openings.append(opening)

            if len(openings) < 2:
                score = 0.5
            else:
                variance = max(openings) - min(openings)
                score = min(variance * 20, 1.0)

            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=True,
                scores={"motion_score": round(score, 3)},
                labels=["mouth_movement_detected"] if score > 0.3 else ["mouth_static"],
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
    register_plugin(MouthMovementDetectorPlugin())
