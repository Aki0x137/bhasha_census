"""Unit tests for shared typed schemas + fake plugin registry."""
from __future__ import annotations

import time
import uuid
import pytest

from shared.schemas.common import ChallengeType, MediaKind, TargetKind, SessionStatus
from shared.schemas.verification_job import VerificationJob, ChallengeParams, MediaRef, VerificationTarget
from shared.schemas.video_evidence import VideoEvidence, VideoEvidenceScores, PluginResult
from shared.schemas.speech_evidence import SpeechEvidence
from shared.schemas.document_evidence import DocumentEvidence
from shared.schemas.evidence_bundle import EvidenceBundle
from shared.schemas.decision import EnrollmentDecision
from shared.schemas.session import EnrollmentSession, CensusProfile


def _now_ms():
    return int(time.time() * 1000)


def _make_params(**kw) -> ChallengeParams:
    defaults = dict(
        challenge_id="c1",
        challenge_type=ChallengeType.LOOK_LEFT_RIGHT,
        prompt_text="Look left then right",
        time_limit_ms=15000,
        min_confidence=0.65,
        max_attempts=2,
    )
    defaults.update(kw)
    return ChallengeParams(**defaults)


def _make_job(media_uri: str = "evidence/demo/sample.jpg") -> VerificationJob:
    return VerificationJob(
        job_id=f"job_{uuid.uuid4().hex[:6]}",
        session_id="sess_test01",
        created_at_ms=_now_ms(),
        media=[MediaRef(media_id="m1", uri=media_uri, kind=MediaKind.PHOTO)],
        params=_make_params(),
        targets=[VerificationTarget(target_id="t1", kind=TargetKind.PRESENCE)],
    )


# ── VerificationJob ──────────────────────────────────────────────────────────

def test_verification_job_round_trip():
    job = _make_job()
    restored = VerificationJob.model_validate_json(job.model_dump_json())
    assert restored.job_id == job.job_id
    assert restored.params.challenge_type == ChallengeType.LOOK_LEFT_RIGHT


def test_verification_job_requires_media():
    with pytest.raises(Exception):
        VerificationJob(
            job_id="j1",
            session_id="s1",
            created_at_ms=_now_ms(),
            media=[],
            params=_make_params(),
        )


def test_verification_target_metadata_max_depth():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        VerificationTarget(
            target_id="t1",
            kind=TargetKind.PRESENCE,
            metadata={"a": {"b": {"c": "deep"}}},
        )


# ── VideoEvidence ────────────────────────────────────────────────────────────

def test_video_evidence_defaults():
    ev = VideoEvidence(
        evidence_id="ev_001",
        job_id="j1",
        session_id="s1",
        timestamp_ms=_now_ms(),
    )
    assert ev.type == "video"
    assert ev.scores.face_present is False
    assert ev.scores.hard_fail_hint is False


def test_plugin_result_ok():
    r = PluginResult(
        plugin_name="face_detector",
        plugin_version="0.1.0",
        ok=True,
        scores={"face_count": 1},
        labels=["single_face"],
    )
    assert r.ok
    assert r.scores["face_count"] == 1


# ── SpeechEvidence ───────────────────────────────────────────────────────────

def test_speech_evidence_round_trip():
    ev = SpeechEvidence(
        evidence_id="ev_sp1",
        session_id="s1",
        challenge_id="c1",
        timestamp_ms=_now_ms(),
        transcript="the sky is blue",
        confidence=0.9,
        phrase_match_score=0.95,
    )
    restored = SpeechEvidence.model_validate_json(ev.model_dump_json())
    assert restored.phrase_match_score == 0.95


# ── DocumentEvidence ─────────────────────────────────────────────────────────

def test_document_evidence_defaults():
    ev = DocumentEvidence(evidence_id="ev_d1", session_id="s1", timestamp_ms=_now_ms())
    assert ev.document_match_score == 0.0


# ── EvidenceBundle ───────────────────────────────────────────────────────────

def test_evidence_bundle_empty():
    bundle = EvidenceBundle(session_id="s1", collected_at_ms=_now_ms())
    assert bundle.video == []
    assert bundle.speech == []
    assert bundle.document == []


# ── Plugin registry ──────────────────────────────────────────────────────────

def test_plugin_registry_resolve_all():
    from services.video.registry import PluginRegistry

    class FakePlugin:
        name = "fake"
        version = "0.0.1"
        capabilities = ["face"]
        def run(self, job, frames):
            return PluginResult(plugin_name=self.name, plugin_version=self.version, ok=True)

    reg = PluginRegistry()
    reg.register(FakePlugin())
    plugins = reg.resolve(None)
    assert len(plugins) == 1


def test_plugin_registry_unknown_raises():
    from services.video.registry import PluginRegistry
    reg = PluginRegistry()
    with pytest.raises(ValueError, match="Unknown plugin"):
        reg.resolve(["not_registered"])


# ── Policy fusion ────────────────────────────────────────────────────────────

def test_policy_approved_happy_path():
    from services.policy.verdict import run_policy
    from shared.schemas.video_evidence import VideoEvidence, VideoEvidenceScores
    from shared.schemas.common import EnrollmentVerdict

    bundle = EvidenceBundle(
        session_id="s1",
        collected_at_ms=_now_ms(),
        video=[VideoEvidence(
            evidence_id="ev_v1", job_id="j1", session_id="s1",
            timestamp_ms=_now_ms(),
            scores=VideoEvidenceScores(face_present=True, face_count=1, quality_score=0.8, spoof_score=0.1),
            reason_codes=["FACE_PRESENT", "QUALITY_OK"],
        )],
        speech=[SpeechEvidence(
            evidence_id="ev_s1", session_id="s1", challenge_id="c1",
            timestamp_ms=_now_ms(), phrase_match_score=0.9, reason_codes=["SPEECH_MATCH_OK"],
        )],
        document=[DocumentEvidence(
            evidence_id="ev_d1", session_id="s1",
            timestamp_ms=_now_ms(), document_match_score=0.85, document_quality_score=0.8,
            reason_codes=["DOC_READABLE", "DOC_MATCH_OK"],
        )],
    )
    decision = run_policy(bundle)
    assert decision.verdict == EnrollmentVerdict.APPROVED


def test_policy_hard_fail_multi_face():
    from services.policy.verdict import run_policy
    from shared.schemas.video_evidence import VideoEvidence, VideoEvidenceScores
    from shared.schemas.common import EnrollmentVerdict

    bundle = EvidenceBundle(
        session_id="s1",
        collected_at_ms=_now_ms(),
        video=[VideoEvidence(
            evidence_id="ev_v1", job_id="j1", session_id="s1",
            timestamp_ms=_now_ms(),
            scores=VideoEvidenceScores(face_present=True, face_count=2, quality_score=0.8, spoof_score=0.1),
            reason_codes=["MULTI_FACE"],
        )],
    )
    decision = run_policy(bundle)
    assert decision.verdict == EnrollmentVerdict.REJECTED


def test_policy_needs_more_evidence():
    from services.policy.verdict import run_policy
    from shared.schemas.common import EnrollmentVerdict, NextAction

    bundle = EvidenceBundle(session_id="s1", collected_at_ms=_now_ms())
    decision = run_policy(bundle)
    assert decision.verdict == EnrollmentVerdict.NEEDS_MORE_EVIDENCE
    assert decision.next_action == NextAction.RETRY


# ── i18n ────────────────────────────────────────────────────────────────────

def test_i18n_message_key_exists_in_both_locales():
    from apps.telegram.i18n.messages import get_message, MESSAGES
    keys = list(MESSAGES["en"].keys())
    for key in keys:
        en = get_message(key, "en")
        hi = get_message(key, "hi")
        assert isinstance(en, str) and len(en) > 0
        assert isinstance(hi, str) and len(hi) > 0


def test_i18n_format_substitution():
    from apps.telegram.i18n.messages import get_message
    msg = get_message("verdict_approved", "en", reasons="FACE_PRESENT")
    assert "FACE_PRESENT" in msg
