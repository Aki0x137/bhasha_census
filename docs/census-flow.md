# Census Bot Flow — questionnaire, OCR, liveness seam

The Telegram census bot walks a household survey, reads an ID card via OCR
(masked, consistency-checked), and launches a liveness Mini App. Entry point:
[`kyc_bot/census_app.py`](../kyc_bot/census_app.py). Related: [`PRD.md`](PRD.md).

## Guardrails (non-negotiable)

- **Sample / your-own data only** — no third parties' real government IDs.
- **ID number masked** to last-4 (`•••• •••• 1234`); the full number is discarded
  in `mask_id`, never stored or logged.
- **No real government / UIDAI / KYC backend.** OCR + name-match are local
  data-quality aids, not identity verification.
- **Name mismatch → human confirmation, never auto-reject** (`CensusRecord.needs_review`).
- **Consent is question #0.**

## The questionnaire (data-driven)

Defined as data in [`kyc_bot/flow/questions.py`](../kyc_bot/flow/questions.py) — edit
the `CENSUS` list to change the survey; the engine needs no changes.

| # | Question | Type |
|---|---|---|
| 0 | Consent | consent |
| 1 | People in the house | number |
| 2 | Owned / Rented / Other | choice |
| 3 | Assets (Bicycle, Two-wheeler, Car, TV, Smartphone, Computer) | multichoice |
| 4 | Head's full name | text |
| 5 | Marital status | choice |
| 6 | Age | number |
| 7 | Sex | choice |
| 8 | Upload Aadhaar/Voter card → OCR (masked) + name confirm | photo_ocr |
| 9 | Liveness check (Mini App) | webapp |

> Religion / caste are in the real census schedule but intentionally excluded from
> this demo. Per-member repetition (loop questions 4–8 per person) is a documented
> extension — the engine is linear today; add a repeat block keyed on question 1.

## Architecture

```
Telegram ── normalize_update ──► census_app (adapter, does I/O)
                                     │  text / choice / photo / webapp
                                     ▼
                        QuestionnaireEngine (pure state machine)
                          next_actions() / submit()  ──►  [Action]  ──► channel renders
                                     │
             photo_ocr ─► DocProvider.digitize() ─► mask_id + name_similarity ─► OcrAnswer
             webapp    ─► send_webapp() ─► liveness Mini App (video track owns detection)
```

- **Engine is pure** (no network/Telegram) → fully unit-tested in `tests/flow/`.
- **OCR provider** swaps via env: `SarvamDocProvider` when `SARVAM_API_KEY` is set
  (with a Fake fallback on any error), else `FakeDocProvider`.
- **Liveness** is a seam: [`kyc_bot/webapp/liveness.html`](../kyc_bot/webapp/liveness.html)
  opens the camera in a Telegram Mini App; the video-intelligence track wires the
  real blink/spoof detection and POSTs the result. Needs public HTTPS (`WEBAPP_URL`).

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env    # then fill TELEGRAM_BOT_TOKEN (SARVAM_API_KEY optional)
python -m kyc_bot.census_app
```

Open the bot in Telegram, send `/start`, and complete the survey. With no
`SARVAM_API_KEY` the OCR step uses a deterministic sample so it runs fully offline.

### Enabling the liveness Mini App

1. Serve `kyc_bot/webapp/liveness.html` over public HTTPS, e.g.
   `cloudflared tunnel --url http://localhost:8000`.
2. Set `WEBAPP_URL` in `.env` to that URL.
3. The liveness step then shows an in-chat **Open camera** button.
   Demo on Telegram Desktop or Android (iOS WebView camera is less reliable).

## Tests

```bash
pytest            # engine happy-path, validation, mismatch-confirm, masking, name-match
```
