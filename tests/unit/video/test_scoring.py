"""Unit tests for video scoring aggregation."""
from __future__ import annotations

from shared.schemas.video_evidence import PluginResult
from shared.schemas.verification_job import VerificationJob
from tests.unit.video.test_schemas import _make_job


def _make_result(name: str = "p", **scores) -> PluginResult:
    return PluginResult(plugin_name=name, plugin_version="0.1", ok=True, scores=scores)


def test_no_face_hard_fail():
    from services.video.scoring import aggregate_scores
    job = _make_job()
    results = [_make_result("face_detector", face_count=0, quality_score=0.8)]
    scores = aggregate_scores(results, job)
    assert not scores.face_present
    assert scores.hard_fail_hint


def test_multi_face_hard_fail():
    from services.video.scoring import aggregate_scores
    job = _make_job()
    results = [_make_result("face_detector", face_count=2, quality_score=0.7)]
    scores = aggregate_scores(results, job)
    assert scores.face_count == 2
    assert scores.hard_fail_hint


def test_single_face_passes():
    from services.video.scoring import aggregate_scores
    job = _make_job()
    results = [_make_result("face_detector", face_count=1, quality_score=0.8)]
    scores = aggregate_scores(results, job)
    assert scores.face_present
    assert not scores.hard_fail_hint


def test_spoof_hard_fail():
    from services.video.scoring import aggregate_scores
    job = _make_job()
    results = [
        _make_result("face_detector", face_count=1, quality_score=0.7),
        _make_result("spoof_detector", spoof_score=0.9),
    ]
    scores = aggregate_scores(results, job)
    assert scores.hard_fail_hint
