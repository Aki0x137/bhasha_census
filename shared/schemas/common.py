"""Shared enums, reason codes, and constants used across all services."""
from enum import Enum


class SessionStatus(str, Enum):
    CREATED = "CREATED"
    CONSENT_PENDING = "CONSENT_PENDING"
    CENSUS_IN_PROGRESS = "CENSUS_IN_PROGRESS"
    CENSUS_COMPLETE = "CENSUS_COMPLETE"
    CHALLENGE_RUNNING = "CHALLENGE_RUNNING"
    SPEECH_CAPTURED = "SPEECH_CAPTURED"
    DOCUMENT_CAPTURED = "DOCUMENT_CAPTURED"
    EVIDENCE_AGGREGATED = "EVIDENCE_AGGREGATED"
    VERDICT_READY = "VERDICT_READY"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class ChallengeType(str, Enum):
    LOOK_LEFT_RIGHT = "LOOK_LEFT_RIGHT"
    BLINK_TWICE = "BLINK_TWICE"
    SMILE_AND_TILT = "SMILE_AND_TILT"
    SAY_RANDOM_PHRASE = "SAY_RANDOM_PHRASE"
    SHOW_ID_AND_READ_FIELD = "SHOW_ID_AND_READ_FIELD"
    CUSTOM = "CUSTOM"


class MediaKind(str, Enum):
    PHOTO = "photo"
    VIDEO_CLIP = "video_clip"
    FRAME_SEQUENCE = "frame_sequence"


class TargetKind(str, Enum):
    PRESENCE = "presence"
    POSE = "pose"
    LIVENESS_CUE = "liveness_cue"
    DOCUMENT_FIELD = "document_field"
    DOCUMENT_VISIBLE = "document_visible"
    ANTI_SPOOF = "anti_spoof"


class TargetStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEFERRED = "deferred"


class EnrollmentVerdict(str, Enum):
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


class NextAction(str, Enum):
    ALLOW = "allow"
    MANUAL_REVIEW = "manual_review"
    RETRY = "retry"


# Reason codes used in VideoEvidence, SpeechEvidence, DocumentEvidence
class ReasonCode(str, Enum):
    # Video
    FACE_PRESENT = "FACE_PRESENT"
    FACE_MISSING = "FACE_MISSING"
    MULTI_FACE = "MULTI_FACE"
    QUALITY_OK = "QUALITY_OK"
    QUALITY_LOW = "QUALITY_LOW"
    CHALLENGE_POSE_OK = "CHALLENGE_POSE_OK"
    CHALLENGE_POSE_FAIL = "CHALLENGE_POSE_FAIL"
    SPOOF_SUSPECT = "SPOOF_SUSPECT"
    REPLAY_SUSPECT = "REPLAY_SUSPECT"
    DOC_FRAME_WEAK = "DOC_FRAME_WEAK"
    DOC_FRAME_OK = "DOC_FRAME_OK"
    PLUGIN_SKIPPED = "PLUGIN_SKIPPED"
    # Speech
    SPEECH_MATCH_OK = "SPEECH_MATCH_OK"
    SPEECH_MISMATCH = "SPEECH_MISMATCH"
    SPEECH_LATENCY_OK = "SPEECH_LATENCY_OK"
    SPEECH_LATENCY_HIGH = "SPEECH_LATENCY_HIGH"
    # Document
    DOC_READABLE = "DOC_READABLE"
    DOC_UNREADABLE = "DOC_UNREADABLE"
    DOC_MATCH_OK = "DOC_MATCH_OK"
    DOC_MISMATCH = "DOC_MISMATCH"
