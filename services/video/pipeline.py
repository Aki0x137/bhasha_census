"""Pluggable video verification pipeline."""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from shared.schemas.common import TargetKind, TargetStatus, ReasonCode
from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import TargetEvaluation, VideoEvidence
from shared.utils.logging import get_logger
from services.video.registry import get_registry
from services.video.scoring import aggregate_scores

logger = get_logger(__name__)


def _load_frames(job: VerificationJob) -> list[Any]:
    """Load media refs into frame objects (numpy arrays for real plugins)."""
    frames: list[Any] = []
    for ref in job.media:
        path = Path(ref.uri)
        if not path.exists():
            raise FileNotFoundError(f"Media not found: {ref.uri}")
        frames.append(str(path))
    return frames


def _evaluate_targets(job: VerificationJob, scores: Any) -> list[TargetEvaluation]:
    evals: list[TargetEvaluation] = []
    for target in job.targets:
        if target.kind == TargetKind.DOCUMENT_FIELD:
            evals.append(
                TargetEvaluation(
                    target_id=target.target_id,
                    status=TargetStatus.DEFERRED,
                    detail="document_field handled by document service",
                )
            )
        elif target.kind == TargetKind.PRESENCE:
            status = TargetStatus.PASSED if scores.face_present else TargetStatus.FAILED
            detail = f"face_count={scores.face_count}"
            evals.append(TargetEvaluation(target_id=target.target_id, status=status, detail=detail))
        elif target.kind == TargetKind.DOCUMENT_VISIBLE:
            if scores.doc_visible_score is None:
                evals.append(TargetEvaluation(target_id=target.target_id, status=TargetStatus.SKIPPED))
            else:
                status = (
                    TargetStatus.PASSED if scores.doc_visible_score >= 0.5 else TargetStatus.FAILED
                )
                evals.append(
                    TargetEvaluation(target_id=target.target_id, status=status,
                                     detail=f"doc_visible={scores.doc_visible_score:.2f}")
                )
        else:
            evals.append(TargetEvaluation(target_id=target.target_id, status=TargetStatus.SKIPPED))
    return evals


def run_verification_job(job: VerificationJob) -> VideoEvidence:
    """Run the full plugin pipeline for one VerificationJob."""
    start = time.monotonic()
    registry = get_registry()

    try:
        plugins = registry.resolve(job.params.enabled_plugins)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    frames = _load_frames(job)
    plugin_results = []
    for plugin in plugins:
        result = plugin.run(job, frames)
        plugin_results.append(result)
        logger.info(
            "plugin_ran",
            plugin=plugin.name,
            ok=result.ok,
            duration_ms=result.duration_ms,
            session_id=job.session_id,
        )

    scores = aggregate_scores(plugin_results, job)
    targets_eval = _evaluate_targets(job, scores)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    evidence_id = f"ev_{uuid.uuid4().hex[:8]}"
    evidence = VideoEvidence(
        evidence_id=evidence_id,
        job_id=job.job_id,
        session_id=job.session_id,
        timestamp_ms=int(time.time() * 1000),
        scores=scores,
        reason_codes=_build_reason_codes(scores),
        plugin_results=plugin_results,
        targets_evaluation=targets_eval,
    )
    logger.info(
        "pipeline_complete",
        job_id=job.job_id,
        session_id=job.session_id,
        elapsed_ms=elapsed_ms,
        hard_fail=scores.hard_fail_hint,
    )
    return evidence


def _build_reason_codes(scores: Any) -> list[str]:
    codes: list[str] = []
    if scores.face_present:
        codes.append(ReasonCode.FACE_PRESENT.value)
        if scores.face_count > 1:
            codes.append(ReasonCode.MULTI_FACE.value)
    else:
        codes.append(ReasonCode.FACE_MISSING.value)
    if scores.quality_score >= 0.6:
        codes.append(ReasonCode.QUALITY_OK.value)
    else:
        codes.append(ReasonCode.QUALITY_LOW.value)
    if scores.spoof_score >= 0.7:
        codes.append(ReasonCode.SPOOF_SUSPECT.value)
    if scores.replay_score >= 0.7:
        codes.append(ReasonCode.REPLAY_SUSPECT.value)
    if scores.pose_match_score is not None:
        if scores.pose_match_score >= 0.6:
            codes.append(ReasonCode.CHALLENGE_POSE_OK.value)
        else:
            codes.append(ReasonCode.CHALLENGE_POSE_FAIL.value)
    if scores.doc_visible_score is not None:
        codes.append(
            ReasonCode.DOC_FRAME_OK.value
            if scores.doc_visible_score >= 0.5
            else ReasonCode.DOC_FRAME_WEAK.value
        )
    return codes
