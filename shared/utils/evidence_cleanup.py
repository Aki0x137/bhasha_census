"""Optional media retention cleanup helper."""
from __future__ import annotations

import os
import time
from pathlib import Path

from shared.utils.evidence_paths import EVIDENCE_ROOT
from shared.utils.logging import get_logger

logger = get_logger(__name__)


def remove_raw_media(session_id: str, max_age_seconds: int = 86400) -> list[str]:
    """Delete raw media files older than max_age_seconds for a session.

    Keeps score/JSON evidence; only removes image/video/audio blobs.
    Returns list of deleted paths.
    """
    raw_exts = {".jpg", ".jpeg", ".mp4", ".webm", ".ogg", ".wav", ".mp3"}
    session_dir = EVIDENCE_ROOT / session_id
    removed: list[str] = []
    now = time.time()
    for path in session_dir.rglob("*"):
        if path.suffix.lower() in raw_exts and path.is_file():
            age = now - path.stat().st_mtime
            if age > max_age_seconds:
                os.remove(path)
                removed.append(str(path))
                logger.info("evidence_cleaned", path=str(path), age_s=int(age))
    return removed
