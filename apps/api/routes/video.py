"""Video routes: GET /video/plugins, POST /video/verify."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import VideoEvidence
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
