"""Temporal activity wrapper for the video verification pipeline."""
from __future__ import annotations

from temporalio import activity

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import VideoEvidence
from shared.utils.logging import get_logger
from services.video.pipeline import run_verification_job

logger = get_logger(__name__)


@activity.defn(name="analyze_verification_job")
async def analyze_verification_job(job: VerificationJob) -> VideoEvidence:
    activity.heartbeat()
    logger.info(
        "activity_started",
        job_id=job.job_id,
        session_id=job.session_id,
        plugins=job.params.enabled_plugins,
    )
    evidence = run_verification_job(job)
    logger.info("activity_complete", evidence_id=evidence.evidence_id)
    return evidence
