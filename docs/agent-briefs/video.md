# Agent Brief — Track B: Video Liveness + Human-vs-AI Detection

> Paste the block below into the video/ML teammate's AI agent. Self-contained.
> Full context: [`docs/PRD.md`](../PRD.md). Shared step first: create `shared/schemas/`
> from PRD §5 (whoever starts first), commit + push, everyone pulls.

```text
You are building the video-intelligence service for "Praman", a local liveness /
anti-deepfake verification MVP. Repo: bhasaha_census (Python 3.11, OpenCV +
MediaPipe; InsightFace optional). FIRST read docs/PRD.md, especially §5 (contracts),
§7 (your track), §8 (policy — you feed it).

Your deliverable (owns services/video/ and optional services/face/):
- Given webcam frames/short clips, produce a typed VideoScores (see PRD §5):
  face_present, track_stable, quality_score, motion_score, spoof_score (human-vs-AI:
  higher = more likely AI/replay), replay_score, challenge_passed.
- Liveness challenges via MediaPipe FaceMesh: blink via eye-aspect-ratio (EAR drop),
  head-turn via yaw, plus frame-quality scoring. challenge_passed = the requested
  motion was performed within the time limit.
- Human-vs-AI / replay heuristics: temporal consistency, frame repetition, unnatural
  motion, screen-of-a-screen cues -> spoof_score / replay_score. Simple, explainable
  heuristics are fine for MVP; no custom model training.
- OPTIONAL (parking-lot-able): services/face/ = InsightFace embedding cosine between
  the sharpest selfie frame and the document photo -> FaceScores.face_sim.

Contract: import types from shared/schemas/; return VideoScores exactly. Do NOT
change shared/schemas/. Expose a plain Python function/class the backend can call
(no HTTP needed inside the service). Provide a FakeVideoProvider returning
deterministic scores so other tracks aren't blocked.

Golden acceptance test: (1) a real webcam clip of a blink-on-cue -> challenge_passed
True, low spoof_score; (2) a replayed video-of-a-video or held-up photo -> replay_score
/ spoof_score clearly rises. Ship a mocked-score fallback path so a model download or
missing camera can never crash the demo.

Guardrails: sample/own faces only; local processing only; no external calls; do not
retain raw video beyond debugging.
```
