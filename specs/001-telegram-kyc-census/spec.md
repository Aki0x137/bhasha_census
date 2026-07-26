# Feature Specification: Telegram KYC & Census Automation MVP

**Feature Branch**: `001-telegram-kyc-census`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "we're building an mvp for kyc/census automation via telegram and ai agents using sarvam and aws bedrock."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start Enrollment and Capture Census Basics (Priority: P1)

A resident opens the project's Telegram bot and starts a new KYC/census
enrollment session. After explicit consent, an AI assistant guides them in
plain language (including Indian languages where available) through a short
set of census questions (identity name, date of birth or age, gender,
locality/address, and household size). Answers are confirmed back to the
user before proceeding.

**Why this priority**: Without guided data capture on Telegram, there is no
enrollment to verify; this is the minimum demonstrable MVP slice.

**Independent Test**: Start a bot conversation, complete consent and the
basic census questions, and confirm a session exists with saved answers and
status showing data capture complete (verification not yet required).

**Acceptance Scenarios**:

1. **Given** a resident has never enrolled, **When** they start the bot and
   accept consent, **Then** the assistant begins the census question flow
   and does not collect media before consent.
2. **Given** the resident is mid-flow, **When** they answer each required
   census question, **Then** the system stores the answer, shows a brief
   confirmation, and advances to the next question.
3. **Given** all basic census fields are answered, **When** the resident
   confirms the summary, **Then** the session is marked ready for identity
   verification challenges.

---

### User Story 2 - Prove Presence with Live Challenges (Priority: P2)

The assistant asks the resident to complete short, randomized live
challenges over Telegram (for example: face photo or short video following
an instruction, and speaking a prompted phrase as a voice message). The
system checks that a real person appears to be present and responding in
time, and that the spoken answer matches the prompt. Results contribute to
an evidence-backed trust decision—not a single pass/fail from one check.

**Why this priority**: KYC automation is unsafe without presence and
anti-spoof signals; this delivers the core “is this a live human?” value.

**Independent Test**: From a session with census basics saved, complete one
physical/presence challenge and one speech challenge; inspect that each
produces a recorded outcome with reason labels usable in a final decision.

**Acceptance Scenarios**:

1. **Given** a session ready for verification, **When** the bot issues a
   physical presence challenge with a time limit, **Then** the resident can
   submit the requested photo or video and receives clear success, retry, or
   failure feedback.
2. **Given** a speech challenge prompt, **When** the resident sends a voice
   message, **Then** the system compares the spoken content to the prompt
   and records match quality and whether the response was timely.
3. **Given** a challenge times out or fails quality checks (no face, unclear
   audio), **When** attempts remain, **Then** the bot offers a limited retry;
   **When** attempts are exhausted, **Then** the session moves toward review
   or fail with an explainable reason—not a silent drop.

---

### User Story 3 - Capture ID Document and Cross-Check Claims (Priority: P3)

The bot asks the resident to photograph a government-issued identity
document. The system extracts readable text/fields and checks consistency
against what the resident already claimed (at least name and date of birth
or age). Mismatches or unreadable documents route to review rather than an
automatic hard pass.

**Why this priority**: Document consistency closes the KYC loop for census
enrollment; it builds on P1 data and P2 presence evidence.

**Independent Test**: Submit a clear document image in an active session and
confirm extracted fields are shown or summarized and compared to prior
answers, with a consistency result stored on the session.

**Acceptance Scenarios**:

1. **Given** a session in document capture, **When** the resident uploads a
   clear ID photo, **Then** the system extracts text/fields and reports
   whether the document was readable.
2. **Given** extracted document fields and prior census answers, **When**
   consistency is evaluated, **Then** matching name/DOB (or age) increases
   trust and material mismatches produce review or fail reason codes.
3. **Given** an unreadable or wrong-type image, **When** processing finishes,
   **Then** the user is asked to retry (within limits) or the case is marked
   for human review.

---

### User Story 4 - Receive an Explainable Enrollment Decision (Priority: P4)

After challenges and document checks, the resident receives a clear
enrollment outcome: approved, needs review, rejected, or needs more
evidence—plus short plain-language reasons. An operator can later open the
same session and see the evidence summary used for the decision.

**Why this priority**: Automation only helps census ops if outcomes are
explainable and reviewable; depends on prior stories for evidence.

**Independent Test**: Complete P1–P3 paths (or inject equivalent evidence in
a test harness) and finalize; confirm the user-facing verdict and that an
operator-readable evidence summary lists the contributing checks.

**Acceptance Scenarios**:

1. **Given** sufficient successful presence, speech, and document evidence
   with no high-risk spoof signals, **When** the session is finalized,
   **Then** the resident is told enrollment is approved with reason labels.
2. **Given** mixed or low-confidence evidence, **When** finalized, **Then**
   the outcome is needs review or needs more evidence—not a silent approve.
3. **Given** hard failures (no face after grace, mandatory phrase mismatch,
   critical spoof suspicion, or exhausted retries), **When** finalized,
   **Then** the outcome is rejected or review with explicit reasons the
   resident can understand at a high level (without exposing internal
   scoring formulas).

---

### Edge Cases

- Resident denies or revokes consent before or during media capture
- Telegram media arrives corrupted, empty, or in an unsupported format
- Multiple faces appear in a submitted photo/video
- Resident switches language mid-flow or sends text when voice was required
- Network interruption mid-challenge; resident resumes the same session
- Partial completion: census answers saved but verification never finished
- Document language differs from the conversation language
- Suspected replay or AI-generated face/voice media
- Concurrent start commands creating duplicate sessions for one Telegram user

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Residents MUST be able to start, resume, and complete an
  enrollment session entirely through the Telegram bot.
- **FR-002**: System MUST obtain explicit consent for data and media
  collection before requesting photos, video, or voice messages.
- **FR-003**: System MUST collect and confirm a minimal census profile:
  full name, date of birth or age, gender, locality/address, and household
  size.
- **FR-004**: An AI assistant MUST guide the conversation, clarify
  questions, summarize answers, and keep the resident oriented on next
  steps without inventing personal facts the resident did not provide.
- **FR-005**: System MUST support conversation in English and at least one
  additional Indian language for prompts and confirmations in the MVP.
- **FR-006**: System MUST issue randomized presence challenges (photo or
  short video following an instruction) with time limits and limited retries.
- **FR-007**: System MUST issue a spoken phrase challenge via voice message
  and evaluate whether the speech content matches the prompt in a timely way.
- **FR-008**: System MUST accept an identity-document image, extract usable
  text/fields, and compare key fields to the resident’s stated identity.
- **FR-009**: System MUST fuse multiple evidence types (presence, speech,
  document, and manipulation/replay risk indicators when available) into a
  single enrollment decision with reason codes.
- **FR-010**: Final enrollment decision MUST be one of: approved, needs
  review, rejected, or needs more evidence—and MUST NOT be based solely on
  an unconstrained AI narrative without rule-backed checks.
- **FR-011**: System MUST persist session state, answers, evidence
  references, and the final decision so an operator can review what
  happened.
- **FR-012**: System MUST handle timeouts, unreadable media, and provider
  failures with user-visible next steps (retry, review, or safe stop) rather
  than failing silently.
- **FR-013**: System MUST prevent a Telegram user from having more than one
  active enrollment session at a time (new start resumes or closes the
  prior active session per product rule).
- **FR-014**: Residents MUST be able to view a short summary of their
  submitted census answers and the final outcome in Telegram after
  finalization.

### Key Entities

- **Enrollment Session**: A single KYC/census attempt for one Telegram
  user; tracks status, consent, timestamps, and final decision.
- **Census Profile**: Minimal demographic/address attributes collected in
  the session and confirmed by the resident.
- **Challenge**: A time-bounded presence or speech task with type, prompt,
  attempts, and outcome.
- **Evidence Item**: A recorded artifact or score from media, speech,
  document extraction, or risk checks, linked to the session.
- **Enrollment Decision**: Verdict, confidence summary, reason codes, and
  recommended next action (allow, manual review, retry).
- **Operator Review Record**: Read-only view of session evidence and
  decision for human follow-up when status is needs review.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new resident can complete consent plus basic census
  questions in under 5 minutes in a guided Telegram conversation.
- **SC-002**: At least 90% of test residents who follow prompts can finish
  one presence challenge and one speech challenge without operator help.
- **SC-003**: For clear, well-lit ID photos in the test set, document text
  usable for name/DOB (or age) comparison is obtained in at least 85% of
  attempts.
- **SC-004**: 100% of finalized sessions show the resident a verdict in
  Telegram with at least one human-readable reason.
- **SC-005**: In scripted happy-path demos, end-to-end enrollment
  (questions + challenges + document + decision) completes in under 15
  minutes.
- **SC-006**: In review sampling, at least 95% of automatic “approved”
  decisions have all required evidence types present and no critical risk
  flags.
- **SC-007**: Operators can open any finalized session and identify which
  challenges passed or failed within 2 minutes without reading raw logs.

## Assumptions

- Primary user for MVP is a resident self-enrolling on Telegram; field
  enumerators may use the same bot later but are not a separate MVP role.
- “KYC” in MVP means presence + speech + document consistency checks suitable
  for a hackathon/demo—not certified e-KYC or Aadhaar/legal identity proofing.
- Minimal census fields listed in FR-003 are sufficient for the MVP; full
  census schedules are deferred.
- Speech understanding, document reading, translation, and AI guidance will
  use the project’s planned providers (Sarvam for speech/document language
  tasks; Bedrock-backed agents for orchestration and explanations), but
  product behavior is defined independently of vendor APIs.
- Residents have a Telegram account, can send photos/voice/video, and have
  intermittent but usable mobile connectivity.
- One active session per Telegram user; abandoned sessions can be resumed
  within a same-day window (default 24 hours) then expire to “needs more
  evidence” or closed.
- Local developer demonstration on Linux/macOS remains the delivery target;
  production-scale Telegram hosting is out of scope for this MVP feature.

## Out of Scope *(mandatory for MVP alignment)*

- Government-grade or legally binding identity proofing / certified e-KYC
- Aadhaar OTP, DigiLocker, or other official identity federation
- Full census questionnaire beyond the minimal profile in FR-003
- Continuous monitoring after the enrollment session ends
- Fraud graph analytics across a large population
- Training custom deepfake or face-matching models from scratch
- Native mobile apps or a browser webcam client as the primary channel
  (Telegram is the MVP channel)
- Multi-operator case-management workflows, SLAs, and production audit
  certifications
- Windows as a supported local runtime

## Privacy & Consent *(mandatory if feature captures camera, mic, or documents)*

- Consent before capture: Bot MUST present a clear consent message covering
  census answers, face photo/video, voice, and ID document image; enrollment
  MUST NOT request media until the resident accepts. Decline ends the flow
  without storing media.
- Retention of raw media: Keep raw media only as long as needed for MVP
  debugging and review; prefer derived scores, transcripts, extracted fields,
  and references for long-lived records.
- Redaction / session-scoped storage: Limit retained document text to fields
  needed for consistency checks; bind prompts, transcripts, and media
  references to the enrollment session; associate every decision with
  traceable evidence identifiers for review.
