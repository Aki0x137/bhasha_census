# MVP Architecture, HLD, and LLD

## Video Liveness + Human vs AI Media Verification System

### 1. Purpose

Build a locally runnable MVP that verifies whether a live video stream is coming from a real human, whether the participant is physically present, whether the feed is likely AI-generated or replayed, and whether the person can complete simple spoken and document-based challenges.

The system uses:

* **Sarvam APIs** for speech-to-text, translation, and document digitization. Sarvam’s docs describe production-ready APIs for transcription, translation, transliteration, text-to-speech, conversational AI, and document digitization, and the streaming STT API is WebSocket-based.
* **AWS Bedrock** for orchestration, policy enforcement, retrieval, and guardrails. Bedrock supports Agents, Knowledge Bases, and Guardrails, and guardrails can be associated with agents and model invocation flows.

### 2. MVP outcomes

The MVP should answer four questions with evidence:

1. Is there a live human face in the camera feed?
2. Does the person respond to random physical and speech challenges in real time?
3. Is the feed likely AI-generated, replayed, or manipulated?
4. If a document is shown, can the system extract text and verify consistency with the user’s spoken answers?

### 3. Scope

#### In scope

* Browser-based webcam and microphone capture
* Live challenge-response flow
* Face tracking and frame quality checks
* Passive deepfake / spoof detection
* Speech transcription using Sarvam Streaming STT
* Spoken word verification
* Document capture, OCR, and document consistency checks using Sarvam Document Digitization
* Risk scoring and final decision
* Local-first developer experience
* Bedrock-powered orchestration and policy layer

#### Out of scope for MVP

* Production identity proofing
* Government-grade biometric compliance
* Large-scale fraud graph analytics
* Continuous background monitoring after session end
* Training custom models from scratch

### 4. High-level architecture

#### 4.1 Main components

**Client app**

* React or Next.js web app
* Captures webcam, microphone, and optional document image upload or live document scan
* Displays prompts to user
* Streams media to backend
* Shows final verification result and evidence summary

**API gateway / backend**

* FastAPI or Node.js service
* Session orchestration
* Challenge generation
* Media routing
* Calls Sarvam and Bedrock
* Aggregates evidence into a session verdict

**Video intelligence service**

* Face detection and tracking
* Frame quality scoring
* Blink / pose / mouth movement heuristics
* Passive spoof / deepfake scoring
* Temporal consistency scoring

**Speech intelligence service**

* Sarvam Streaming STT over WebSocket for live speech answers. Sarvam explicitly documents real-time speech-to-text via WebSocket, plus REST and batch modes.
* Prompt answer matching
* Keyword and sequence verification

**Document intelligence service**

* Sarvam Document Digitization to extract structured text and table data from documents. Sarvam’s document digitization docs describe text extraction, structure preservation, table parsing, and machine-readable HTML or Markdown output.
* Optional translation to canonical language using Sarvam translation APIs
* Document text consistency checks against user claims

**Bedrock orchestration layer**

* Generates randomized challenges
* Applies guardrails to prompts and responses
* Summarizes evidence
* Produces final decision and reason codes
* Optional Knowledge Base for prompt templates, policy rules, fraud patterns, and verification playbooks. Bedrock Knowledge Bases support secure retrieval over datasets, and Bedrock Agents have pre-processing, orchestration, knowledge base response generation, and post-processing steps.

**Storage**

* Local SQLite for MVP metadata
* Object storage locally via filesystem, or S3 in cloud mode
* Evidence snapshots, transcripts, OCR output, decision logs

### 5. Trust model and decision strategy

Do not rely on one signal. The system should fuse independent evidence:

* **Presence evidence**: a face is detected, stable, and trackable
* **Challenge evidence**: user successfully performs random actions
* **Speech evidence**: spoken phrases match the prompted words with low latency
* **Document evidence**: extracted text matches claims or required identifiers
* **Deepfake evidence**: passive detector scores indicate manipulated or synthetic media
* **Replay evidence**: frame repetition, unnatural motion, or audio-video mismatch

Final verdicts:

* **PASS**
* **REVIEW**
* **FAIL**
* **NEEDS MORE EVIDENCE**

Recommended default rule:

* PASS only if at least one active challenge, one speech challenge, and one document challenge succeed, and no high-confidence spoof signal exists.
* REVIEW if evidence is mixed or low-confidence.
* FAIL if multiple branches fail or spoof confidence crosses threshold.

### 6. HLD

#### 6.1 Runtime flow

1. User opens the local web app.
2. Browser requests a verification session.
3. Backend creates a session and generates a challenge plan.
4. Client starts webcam and microphone capture.
5. Backend receives live metadata and selected frames or clips.
6. Backend asks the user to do physical actions.
7. Backend asks the user to say random words or a random phrase.
8. Backend asks the user to show a document.
9. Sarvam STT transcribes the spoken response in real time.
10. Sarvam Document Digitization extracts document text and structure.
11. Bedrock orchestrator combines all evidence and emits the final verdict, with guardrails applied to prompts and responses.

#### 6.2 Suggested deployment for local MVP

* `frontend`: browser app on localhost
* `backend-api`: local service
* `video-worker`: local Python worker
* `speech-worker`: local integration worker for Sarvam STT
* `doc-worker`: local integration worker for Sarvam Doc Digitization
* `orchestrator-worker`: local Bedrock client
* `sqlite.db`
* `evidence/` directory for local snapshots

#### 6.3 Data flow

**Video path**
Camera -> frontend -> backend -> video-worker -> risk scores -> orchestrator

**Speech path**
Microphone -> frontend -> backend -> Sarvam STT -> transcript -> phrase verifier -> orchestrator

**Document path**
Camera or upload -> frontend -> backend -> Sarvam document digitization -> extracted text -> document verifier -> orchestrator

**LLM path**
Aggregated evidence -> Bedrock agent or model call -> final reasoning and decision -> verdict JSON

### 7. LLD

## 7.1 Services and responsibilities

### A. Session Service

Responsibilities:

* Create, update, close verification sessions
* Store session state
* Issue a challenge plan
* Track timestamps and evidence references

Core fields:

* `session_id`
* `user_ref`
* `status`
* `challenge_plan`
* `start_time`
* `end_time`
* `final_verdict`

### B. Challenge Engine

Responsibilities:

* Generate randomized prompts
* Ensure challenges are non-repeating
* Support three challenge types:

  * physical action
  * speech phrase
  * document readback

Challenge types:

* `LOOK_LEFT_RIGHT`
* `BLINK_TWICE`
* `SMILE_AND_TILT`
* `SAY_RANDOM_PHRASE`
* `READ_DOCUMENT_TEXT`
* `SHOW_ID_AND_READ_FIELD`

Challenge objects should contain:

* `challenge_id`
* `type`
* `prompt_text`
* `expected_response`
* `time_limit_ms`
* `min_confidence`
* `max_attempts`

### C. Video Intelligence Service

Responsibilities:

* Detect face
* Track face across frames
* Score image quality
* Detect motion consistency
* Detect liveness cues
* Score spoof probability

Recommended submodules:

* `face_detector`
* `face_tracker`
* `frame_quality_scoring`
* `pose_estimator`
* `blink_detector`
* `mouth_movement_detector`
* `spoof_detector`
* `temporal_anomaly_detector`

Key outputs:

* `face_present: bool`
* `track_stable: bool`
* `quality_score: float`
* `motion_score: float`
* `spoof_score: float`
* `replay_score: float`

### D. Speech Intelligence Service

Responsibilities:

* Stream audio to Sarvam STT
* Normalize transcript
* Match prompt vs transcript
* Extract response latency
* Detect repeated or pre-recorded speech patterns

Sarvam’s docs state that streaming STT is WebSocket-based and designed for immediate speech processing.

Key outputs:

* `transcript`
* `confidence`
* `latency_ms`
* `keyword_match_score`
* `phrase_match_score`

### E. Document Intelligence Service

Responsibilities:

* Receive image or frame containing document
* Run Sarvam Document Digitization
* Normalize output
* Extract fields
* Compare against expected claims or policy rules

Sarvam’s Document Digitization API is documented to extract text, preserve structure, parse tables, and output structured HTML or Markdown.

Key outputs:

* `document_text`
* `structured_output`
* `detected_fields`
* `document_quality_score`
* `document_match_score`

### F. Orchestration Service

Responsibilities:

* Merge all evidence
* Call Bedrock model or agent
* Apply deterministic scoring
* Produce final verdict and reason codes

Bedrock Agents support multiple prompt stages, including pre-processing, orchestration, knowledge base response generation, and post-processing, and guardrails can be attached to agents and invoke flows.

### G. Policy Engine

Responsibilities:

* Translate evidence into decision policy
* Provide explainable rules
* Keep final decision deterministic

Example rules:

* If face is missing for more than `N` seconds, fail
* If speech answer does not match prompt within tolerance, fail
* If document cannot be parsed, mark review
* If spoof score is high and active challenge also fails, fail
* If evidence is ambiguous, mark review

### 8. Proposed API contracts

## 8.1 Session APIs

### `POST /sessions`

Creates a new verification session.

Request:

```json
{
  "user_ref": "optional-external-id",
  "mode": "mvp",
  "locale": "en-IN"
}
```

Response:

```json
{
  "session_id": "sess_123",
  "status": "created",
  "challenge_plan": [
    {"challenge_id": "c1", "type": "LOOK_LEFT_RIGHT"},
    {"challenge_id": "c2", "type": "SAY_RANDOM_PHRASE"},
    {"challenge_id": "c3", "type": "SHOW_ID_AND_READ_FIELD"}
  ]
}
```

### `POST /sessions/{session_id}/event`

Accepts client events.

Event examples:

* `video_frame`
* `audio_chunk`
* `challenge_completed`
* `document_captured`
* `client_quality_report`

### `GET /sessions/{session_id}`

Returns session state and evidence summary.

### `POST /sessions/{session_id}/finalize`

Triggers orchestration and verdict generation.

## 8.2 Evidence object schema

```json
{
  "evidence_id": "ev_001",
  "session_id": "sess_123",
  "type": "video|audio|document|challenge",
  "timestamp_ms": 1712345678901,
  "source": "client|sarvam|bedrock|worker",
  "payload_ref": "local-path-or-object-key",
  "scores": {
    "quality": 0.92,
    "spoof": 0.11,
    "match": 0.87
  }
}
```

## 8.3 Verdict schema

```json
{
  "session_id": "sess_123",
  "verdict": "PASS|REVIEW|FAIL|NEEDS_MORE_EVIDENCE",
  "confidence": 0.0,
  "reason_codes": [
    "FACE_PRESENT",
    "SPEECH_MATCH_OK",
    "DOCUMENT_MATCH_OK"
  ],
  "evidence_summary": {
    "video": {},
    "speech": {},
    "document": {}
  },
  "next_action": "allow|manual_review|retry"
}
```

### 9. Bedrock usage pattern

For the MVP, use Bedrock in one of two ways:

#### Option A: Bedrock model call only

* Backend sends the evidence summary to a Bedrock model
* The model produces a structured recommendation
* The policy engine makes the final call

#### Option B: Bedrock Agent

* The agent receives session evidence
* It can consult a Knowledge Base for rules and prompt templates
* Guardrails filter harmful or unexpected content
* Final model response is converted into a structured verdict

Bedrock Knowledge Bases are intended for secure retrieval over large datasets, and Bedrock also supports model invocation logging to CloudWatch Logs and S3.

Recommended MVP choice:

* Use **Option A** first for simplicity
* Add **Option B** after the local flow is stable

### 10. Local developer workflow

#### Recommended repo layout

```text
repo/
  apps/
    web/
    api/
  services/
    video/
    speech/
    document/
    orchestrator/
    policy/
  shared/
    schemas/
    utils/
    prompts/
  infra/
    local/
    aws/
  tests/
    unit/
    integration/
    e2e/
  evidence/
  docs/
```

#### Local run order

1. Start backend API
2. Start video worker
3. Start speech worker
4. Start document worker
5. Start frontend
6. Create a session
7. Run each challenge branch
8. Inspect verdict in UI and logs

### 11. Model and tool choices

#### Video

For MVP, start with:

* OpenCV
* MediaPipe Face Mesh or equivalent face landmarks
* Simple temporal heuristics
* Optional lightweight spoof detector

#### Speech

* Sarvam Streaming STT for live phrase verification. Sarvam documents real-time speech-to-text over WebSocket and supports synchronous, batch, and streaming modes.

#### Document

* Sarvam Document Digitization for OCR and structure extraction. Sarvam describes this API as capable of text extraction, layout preservation, table parsing, and structured output.

#### Orchestration

* AWS Bedrock model or agent
* Guardrails enabled
* Optional Knowledge Base for prompt and policy retrieval. Bedrock guardrails can be associated with agents and model invocations.

### 12. Prompting design

Use Bedrock prompts for:

* challenge generation
* evidence summarization
* final decision explanation
* retry instructions

Prompt template should always include:

* session id
* challenge history
* transcript snippets
* document excerpts
* video quality stats
* spoof scores
* policy rules

System prompt should enforce:

* return structured JSON only
* do not invent facts
* use only provided evidence
* include reason codes
* separate confidence from verdict

### 13. Deterministic scoring

Suggested scoring weights:

* video liveness: 30%
* active challenge success: 30%
* speech match: 20%
* document match: 20%

Suggested thresholds:

* `PASS >= 0.80` and no hard failure
* `REVIEW >= 0.55` and < 0.80
* `FAIL < 0.55` or any hard-fail rule triggered

Hard-fail rules:

* no face detected after grace period
* challenge timeout
* transcript mismatch on mandatory phrase
* document unreadable
* spoof score above critical threshold

### 14. State machine

Session states:

* `CREATED`
* `CAMERA_READY`
* `FACE_DETECTED`
* `CHALLENGE_RUNNING`
* `SPEECH_CAPTURED`
* `DOCUMENT_CAPTURED`
* `EVIDENCE_AGGREGATED`
* `VERDICT_READY`
* `COMPLETED`

Transitions should be monotonic, with retries only inside challenge states.

### 15. Error handling

Handle these failures explicitly:

* camera permission denied
* microphone permission denied
* Sarvam API timeout
* invalid audio stream
* document not visible
* multiple faces detected
* prompt not answered in time
* Bedrock invocation failure

Fallback behaviors:

* retry once for transient failures
* downgrade to REVIEW for partial failures
* store evidence snapshots for later manual review

### 16. Observability

Log the following:

* session lifecycle events
* challenge timestamps
* Sarvam request ids
* Bedrock request ids
* latency per branch
* final verdict
* false positive / false negative review labels

Bedrock supports model invocation logging to CloudWatch Logs and S3.

### 17. Security and privacy

* Do not store raw video longer than necessary for MVP debugging
* Encrypt evidence at rest in cloud mode
* Redact document text not needed for verification
* Keep prompts and transcripts in session-scoped storage
* Associate every verdict with traceable evidence ids
* Add explicit consent screens before camera and mic capture

### 18. Acceptance criteria for MVP

The MVP is complete when:

* A session can be created locally
* The user can complete 3 challenge types
* Sarvam STT returns usable transcripts for live speech responses.
* Sarvam document digitization extracts text from a captured document.
* Bedrock returns a structured verdict explanation with guardrails enabled.
* The system outputs PASS, REVIEW, or FAIL with reason codes
* Evidence is persisted locally for replay and debugging

### 19. Implementation plan for coding agents

#### Phase 1

* Scaffold repo
* Build session API
* Build webcam and microphone UI
* Add local evidence store

#### Phase 2

* Add face detection and liveness heuristics
* Add challenge engine
* Add speech streaming to Sarvam STT

#### Phase 3

* Add document capture and Sarvam digitization
* Add document verification rules
* Add local verdict UI

#### Phase 4

* Add Bedrock orchestration
* Add guardrails
* Add structured verdict generation

#### Phase 5

* Add tests, metrics, and replay tooling
* Harden error handling
* Prepare for cloud deployment

### 20. Recommended first build sequence

For fastest MVP value:

1. Build session API and UI
2. Implement challenge engine
3. Integrate Sarvam STT
4. Integrate Sarvam document digitization
5. Add heuristic liveness checks
6. Add Bedrock verdict summarizer
7. Add policy-based final decision

### 21. Notes for coding agents

* Keep every service stateless except session persistence
* Prefer JSON schemas for all cross-service payloads
* Make challenge generation deterministic under test seeds
* Record every raw model output before post-processing
* Separate extraction, scoring, and decision layers
* Never let the LLM be the only source of truth

### 22. Final recommendation

For this MVP, the cleanest architecture is:

* **Sarvam** for real-time speech and document understanding
* **Bedrock** for orchestration, guardrails, retrieval, and structured reasoning
* **Deterministic policy engine** for the final pass or fail decision
* **Local workers** for video liveness and spoof heuristics

That gives you a practical, agent-friendly system that is easy to build locally, easy to test, and easy to extend later into a cloud deployment.
