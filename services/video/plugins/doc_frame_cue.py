"""Document frame cue plugin — detects card-like rectangles in frame (heuristic)."""
from __future__ import annotations

import time
from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult


class DocFrameCuePlugin:
    name = "doc_frame_cue"
    version = "0.1.0"
    capabilities = ["document_visible"]

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult:
        t0 = time.monotonic()
        try:
            import cv2
            import numpy as np

            doc_scores: list[float] = []
            for frame_path in frames:
                img = cv2.imread(str(frame_path))
                if img is None:
                    continue
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                h, w = gray.shape
                img_area = h * w
                best = 0.0
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area < img_area * 0.05:
                        continue
                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                    if len(approx) == 4:
                        ratio = area / img_area
                        # ID-card-like ratio: 0.1–0.6 of frame area
                        score = min(ratio / 0.4, 1.0) if 0.08 <= ratio <= 0.65 else 0.3
                        best = max(best, score)
                doc_scores.append(best)

            avg = (sum(doc_scores) / len(doc_scores)) if doc_scores else 0.0
            return PluginResult(
                plugin_name=self.name, plugin_version=self.version, ok=True,
                scores={"doc_visible_score": round(avg, 3)},
                labels=["doc_visible"] if avg >= 0.5 else ["doc_not_visible"],
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
    register_plugin(DocFrameCuePlugin())
