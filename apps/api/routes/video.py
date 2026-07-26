"""Video routes: GET /video/plugins, POST /video/verify, POST /video/verify-live."""
from __future__ import annotations

import tempfile
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from shared.schemas.common import ChallengeType, MediaKind, TargetKind
from shared.schemas.verification_job import (
    ChallengeParams,
    MediaRef,
    VerificationJob,
    VerificationTarget,
)
from shared.schemas.video_evidence import VideoEvidence
from services.policy.challenge_engine import build_challenge_params
from services.video.pipeline import run_verification_job
from services.video.registry import get_registry

router = APIRouter(prefix="/video", tags=["video"])


@router.get("/plugins")
def list_plugins() -> dict:
    return {"plugins": get_registry().list_plugins()}


@router.post("/verify", response_model=VideoEvidence)
def verify(job: VerificationJob) -> VideoEvidence:
    registry = get_registry()
    if job.params.enabled_plugins:
        unknown = [n for n in job.params.enabled_plugins if registry.get(n) is None]
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unknown plugins: {unknown}"
            )
    try:
        return run_verification_job(job)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"detail": "pipeline_error", "job_id": job.job_id, "error": str(exc)},
        ) from exc


@router.post("/verify-live")
async def verify_live(
    challenge_type: str = Form("LOOK_LEFT_RIGHT"),
    session_id: str = Form(None),
    frames: List[UploadFile] = File(...),
) -> JSONResponse:
    """Accept webcam frames from the browser liveness page and run the full plugin pipeline.

    Frames are JPEG/PNG images captured at ~1 fps during the challenge window.
    Returns the full VideoEvidence JSON so the page can render scores + reason codes.
    """
    if not frames:
        raise HTTPException(status_code=422, detail="At least one frame is required")

    try:
        ct = ChallengeType(challenge_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown challenge_type '{challenge_type}'. "
            f"Valid: {[e.value for e in ChallengeType]}",
        )

    sess_id = session_id or f"live_{uuid.uuid4().hex[:8]}"
    challenge_id = f"{sess_id}_live"
    job_id = f"job_{uuid.uuid4().hex[:10]}"

    with tempfile.TemporaryDirectory(prefix="bhasaha_live_") as tmp:
        tmp_dir = Path(tmp)
        media_refs: list[MediaRef] = []

        for i, upload in enumerate(frames[:10]):  # cap at 10 frames
            suffix = Path(upload.filename or "frame.jpg").suffix or ".jpg"
            dest = tmp_dir / f"frame_{i:02d}{suffix}"
            dest.write_bytes(await upload.read())
            media_refs.append(
                MediaRef(
                    media_id=f"m_{i:02d}",
                    uri=str(dest),
                    kind=MediaKind.VIDEO_CLIP if i > 0 else MediaKind.PHOTO,
                    captured_at_ms=int(time.time() * 1000) + i * 1000,
                )
            )

        params = build_challenge_params(challenge_id, ct)
        targets = [
            VerificationTarget(
                target_id=f"{challenge_id}_presence",
                kind=TargetKind.PRESENCE,
                required=True,
            )
        ]

        job = VerificationJob(
            job_id=job_id,
            session_id=sess_id,
            locale="en-IN",
            created_at_ms=int(time.time() * 1000),
            media=media_refs,
            params=params,
            targets=targets,
        )

        try:
            evidence = run_verification_job(job)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={"detail": "pipeline_error", "job_id": job_id, "error": str(exc)},
            ) from exc

    return JSONResponse(content=evidence.model_dump())
