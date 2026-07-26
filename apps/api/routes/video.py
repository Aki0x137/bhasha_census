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
    chat_id: str = Form(None),
    frames: List[UploadFile] = File(...),
) -> JSONResponse:
    """Accept webcam frames from the browser liveness page and run the full plugin pipeline.

    Frames are JPEG/PNG images captured at ~1 fps during the challenge window.
    After running the pipeline:
      - Evidence is persisted to the evidence directory as JSON
      - The enrollment session (if session_id is a known sess_* id) is updated
      - If chat_id is provided, the result is pushed back to the Telegram chat
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

        for i, upload in enumerate(frames[:10]):
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

    # ── Persist evidence to disk ────────────────────────────────────────────
    _persist_evidence(evidence)

    # ── Update enrollment session in DB ────────────────────────────────────
    if sess_id.startswith("sess_"):
        _update_session(sess_id, evidence)

    # ── Notify Telegram chat with result ───────────────────────────────────
    if chat_id:
        await _notify_telegram(chat_id, evidence, ct)

    return JSONResponse(content=evidence.model_dump())


def _persist_evidence(evidence) -> None:
    """Save VideoEvidence JSON to evidence/<session_id>/video/<evidence_id>.json."""
    import json
    from shared.utils.evidence_paths import session_video_dir
    try:
        out_dir = session_video_dir(evidence.session_id)
        out_path = out_dir / f"{evidence.evidence_id}.json"
        out_path.write_text(json.dumps(evidence.model_dump(), indent=2))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("evidence_persist_failed: %s", exc)


def _update_session(session_id: str, evidence) -> None:
    """Mark the temp verify challenge complete and store evidence_id on session."""
    try:
        from apps.api.db.session_store import get_session, update_session
        from shared.schemas.common import SessionStatus
        sess = get_session(session_id)
        if not sess:
            return
        if evidence.evidence_id not in sess.evidence_ids:
            sess.evidence_ids.append(evidence.evidence_id)
        # Mark the challenge item done
        for item in sess.challenge_plan:
            if not item.completed:
                item.completed = True
                item.outcome = "passed" if not evidence.scores.hard_fail_hint else "failed"
                break
        # Advance status if all challenges done
        if all(i.completed for i in sess.challenge_plan):
            sess.status = SessionStatus.EVIDENCE_AGGREGATED
        update_session(sess)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("session_update_failed: %s", exc)


async def _notify_telegram(chat_id: str, evidence, ct: ChallengeType) -> None:
    """Push liveness result back to the Telegram chat via Bot API."""
    import os
    import httpx

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        return

    s = evidence.scores
    outcome = "✅ *PASSED*" if not s.hard_fail_hint else "❌ *FAILED*"
    reasons = ", ".join(evidence.reason_codes) or "—"
    plugins_ok  = sum(1 for p in evidence.plugin_results if p.ok)
    plugins_all = len(evidence.plugin_results)

    text = (
        f"🎥 *Liveness Check Result* — {ct.value}\n\n"
        f"Verdict: {outcome}\n\n"
        f"• Face detected: `{'yes' if s.face_present else 'no'}` (count: `{s.face_count}`)\n"
        f"• Quality: `{s.quality_score:.0%}`\n"
        f"• Spoof risk: `{s.spoof_score:.0%}`\n"
        + (f"• Pose match: `{s.pose_match_score:.0%}`\n" if s.pose_match_score is not None else "")
        + f"• Plugins: `{plugins_ok}/{plugins_all}` OK\n"
        f"• Reasons: `{reasons}`\n\n"
        f"evidence\\_id: `{evidence.evidence_id}`\n\n"
        + ("✅ Liveness passed! Type */done* to get your enrollment verdict."
           if not s.hard_fail_hint
           else "❌ Liveness failed. Go back to the browser page and retry, or type */done* to proceed anyway.")
    )

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("telegram_notify_failed: %s", exc)
