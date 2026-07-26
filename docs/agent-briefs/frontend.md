# Agent Brief — Track A: Frontend + Capture UX

> Paste the block below into the frontend teammate's AI agent. Self-contained.
> Full context: [`docs/PRD.md`](../PRD.md). Shared step first: create `shared/schemas/`
> from PRD §5 (whoever starts first), commit + push, everyone pulls.

```text
You are building the frontend for "Praman", a local liveness / anti-deepfake
verification MVP. Repo: bhasaha_census (Python + FastAPI backend, plain
HTML/JS or Vite+React frontend). FIRST read docs/PRD.md fully, especially §4
(HLD/sequence), §5 (contracts), §6 (REST API), §10 (demo script).

Your deliverable (owns apps/web/ ONLY):
- A single-page browser app that: (1) shows a CONSENT screen before any capture;
  (2) requests webcam+mic via getUserMedia; (3) calls POST /sessions, renders the
  returned challenge_plan; (4) for each challenge, shows the prompt and captures
  the right media (video frames for blink/head-turn via MediaRecorder, audio for
  SAY_RANDOM_PHRASE, an image for SHOW_ID_AND_READ_FIELD); (5) POSTs to
  /sessions/{id}/event; (6) calls /finalize and renders a VERDICT card
  (PASS/REVIEW/FAIL) with reason_codes + an evidence panel.

Contract: talk to the backend using the exact REST shapes in PRD §6 and the
Pydantic models in §5. Do NOT change shared/schemas/. Do NOT touch backend or
services/ code.

Work fake-first: run the backend in fake mode (it returns canned scores) so you
are never blocked. Your golden acceptance test: with the API in fake mode, a user
completes a full session in the browser and sees a PASS verdict card with reason
codes. Make the verdict/evidence view demo-clean (this is on the projector).

Guardrails (non-negotiable): consent screen is mandatory and comes first; show ID
numbers masked (XXXX XXXX 1234) if the backend returns them; sample/own data only.
Do NOT build: Telegram/any messaging UI, login/accounts, cloud deploy.
```
