"""MediaPipe compatibility helpers.

MediaPipe >=0.10.30 on some platforms (notably Python 3.14 wheels) ships only the
Tasks API and no longer exposes ``mediapipe.solutions``. Face count helpers fall
back to OpenCV Haar cascades when Solutions is unavailable.
"""
from __future__ import annotations

from typing import Any


def has_solutions() -> bool:
    try:
        import mediapipe as mp

        return hasattr(mp, "solutions")
    except ImportError:
        return False


def count_faces_in_bgr(img: Any) -> int:
    """Return number of faces detected in a BGR OpenCV image."""
    import cv2

    if img is None:
        return 0

    try:
        import mediapipe as mp

        if hasattr(mp, "solutions"):
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            with mp.solutions.face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5
            ) as det:
                results = det.process(img_rgb)
                return len(results.detections) if results.detections else 0
    except Exception:
        pass

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        return 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
    return len(faces)
