"""Evidence directory path helpers."""
from __future__ import annotations

import os
from pathlib import Path

EVIDENCE_ROOT = Path(os.getenv("EVIDENCE_ROOT", "evidence"))


def session_video_dir(session_id: str) -> Path:
    p = EVIDENCE_ROOT / session_id / "video"
    p.mkdir(parents=True, exist_ok=True)
    return p


def session_speech_dir(session_id: str) -> Path:
    p = EVIDENCE_ROOT / session_id / "speech"
    p.mkdir(parents=True, exist_ok=True)
    return p


def session_document_dir(session_id: str) -> Path:
    p = EVIDENCE_ROOT / session_id / "document"
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_debug_path(session_id: str, job_id: str, ext: str = "jpg") -> Path:
    return session_video_dir(session_id) / f"{job_id}_debug.{ext}"
