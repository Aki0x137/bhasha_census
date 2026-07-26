"""Aggregate plugin results into typed VideoEvidenceScores."""
from __future__ import annotations

from typing import Any

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult, VideoEvidenceScores

_HARD_FAIL_SPOOF = 0.85
_HARD_FAIL_NO_FACE = True


def aggregate_scores(
    plugin_results: list[PluginResult], job: VerificationJob
) -> VideoEvidenceScores:
    scores = VideoEvidenceScores()
    pose_scores: list[float] = []
    doc_scores: list[float] = []
    spoof_scores: list[float] = []
    replay_scores: list[float] = []
    quality_scores: list[float] = []
    motion_scores: list[float] = []

    for r in plugin_results:
        if not r.ok:
            continue
        s = r.scores
        if "face_count" in s:
            count = int(s["face_count"])
            scores.face_count = max(scores.face_count, count)
            if count >= 1:
                scores.face_present = True
        if "track_stable" in s:
            scores.track_stable = scores.track_stable or bool(s["track_stable"])
        if "quality_score" in s:
            quality_scores.append(float(s["quality_score"]))
        if "motion_score" in s:
            motion_scores.append(float(s["motion_score"]))
        if "spoof_score" in s:
            spoof_scores.append(float(s["spoof_score"]))
        if "replay_score" in s:
            replay_scores.append(float(s["replay_score"]))
        if "pose_match_score" in s:
            pose_scores.append(float(s["pose_match_score"]))
        if "doc_visible_score" in s:
            doc_scores.append(float(s["doc_visible_score"]))

    if quality_scores:
        scores.quality_score = sum(quality_scores) / len(quality_scores)
    if motion_scores:
        scores.motion_score = sum(motion_scores) / len(motion_scores)
    if spoof_scores:
        scores.spoof_score = max(spoof_scores)  # conservative: take worst
    if replay_scores:
        scores.replay_score = max(replay_scores)
    if pose_scores:
        scores.pose_match_score = sum(pose_scores) / len(pose_scores)
    if doc_scores:
        scores.doc_visible_score = sum(doc_scores) / len(doc_scores)

    spoof_threshold = job.params.spoof_max if job.params.spoof_max is not None else _HARD_FAIL_SPOOF
    quality_threshold = job.params.quality_min if job.params.quality_min is not None else 0.3

    hard_fail = (
        (not scores.face_present)
        or (scores.face_count > 1)
        or (scores.spoof_score >= spoof_threshold)
        or (scores.quality_score < quality_threshold and quality_scores)
    )
    scores.hard_fail_hint = hard_fail
    return scores
