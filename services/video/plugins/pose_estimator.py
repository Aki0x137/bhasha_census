"""Pose estimator plugin — coarse head pose for LOOK_LEFT/RIGHT challenges."""
from __future__ import annotations

import time
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult
from shared.schemas.common import ChallengeType


class PoseEstimatorPlugin:
    name = "pose_estimator"
    version = "0.1.0"
    capabilities = ["pose", "liveness_cue"]

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()
        try:
            import cv2
            import mediapipe as mp
            import numpy as np

            from services.video.mediapipe_compat import has_solutions

            if not has_solutions():
                return PluginResult(
                    plugin_name=self.name,
                    plugin_version=self.version,
                    ok=True,
                    scores={"pose_match_score": 0.5},
                    labels=["pose_skipped_no_mediapipe_solutions"],
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )

            mp_face_mesh = mp.solutions.face_mesh
            pose_scores: list[float] = []
            challenge_type = job.params.challenge_type

            for frame_path in frames:
                img = cv2.imread(str(frame_path))
                if img is None:
                    continue
                h, w = img.shape[:2]
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as mesh:
                    result = mesh.process(img_rgb)
                    if not result.multi_face_landmarks:
                        pose_scores.append(0.0)
                        continue
                    lms = result.multi_face_landmarks[0].landmark
                    # Nose tip (1) vs left (234) and right (454) ear landmarks
                    nose_x = lms[1].x
                    left_x = lms[234].x
                    right_x = lms[454].x
                    face_width = right_x - left_x
                    if face_width < 1e-6:
                        pose_scores.append(0.5)
                        continue
                    offset = (nose_x - (left_x + right_x) / 2) / face_width

                    if challenge_type == ChallengeType.LOOK_LEFT_RIGHT:
                        # Reward any significant lateral offset
                        score = min(abs(offset) * 4, 1.0)
                    elif challenge_type in (ChallengeType.BLINK_TWICE, ChallengeType.SMILE_AND_TILT):
                        score = 0.7  # heuristic — blink/smile need video frames
                    else:
                        score = 0.5
                    pose_scores.append(score)

            avg = (sum(pose_scores) / len(pose_scores)) if pose_scores else 0.5
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=True,
                scores={"pose_match_score": round(avg, 3)},
                labels=["pose_ok"] if avg >= 0.5 else ["pose_fail"],
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
    register_plugin(PoseEstimatorPlugin())
