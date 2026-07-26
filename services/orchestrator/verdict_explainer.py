"""Bedrock-backed enrollment verdict explainer.

Generates a structured JSON explanation of the verdict using the configured
Bedrock model (BEDROCK_MODEL_ID env var, defaults to amazon.nova-pro-v1:0).

LLM is NOT the final authority — the policy verdict is deterministic.
Bedrock provides a human-readable summary bound to the evidence only.

Falls back to a deterministic stub on BedrockOfflineError (no credentials,
model not enabled, etc.) so the enrollment flow is never blocked by Bedrock.
"""
from __future__ import annotations

import json

from shared.schemas.decision import EnrollmentDecision
from shared.schemas.evidence_bundle import EvidenceBundle
from shared.utils.logging import get_logger

from services.orchestrator.bedrock_client import BedrockClient, BedrockOfflineError

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a census enrollment assistant. "
    "Summarize the enrollment outcome in JSON. "
    "Output ONLY a JSON object with keys: "
    "\"summary\" (1-2 sentences) and \"reasons\" (list of strings). "
    "Do NOT invent facts not present in the evidence. "
    "Do NOT override the verdict."
)


def _build_prompt(decision: EnrollmentDecision, bundle: EvidenceBundle) -> str:
    return (
        f"Verdict: {decision.verdict.value}\n"
        f"Confidence: {decision.confidence:.0%}\n"
        f"Reason codes: {', '.join(decision.reason_codes)}\n"
        f"Evidence scores: {json.dumps(decision.evidence_summary)}\n\n"
        "Respond with valid JSON only."
    )


def _fake_explain(decision: EnrollmentDecision) -> dict:
    """Deterministic fallback when Bedrock is unavailable."""
    return {
        "summary": (
            f"Enrollment {decision.verdict.value} with confidence "
            f"{decision.confidence:.0%}."
        ),
        "reasons": decision.reason_codes,
    }


def explain_verdict(decision: EnrollmentDecision, bundle: EvidenceBundle) -> dict:
    """Return a structured explanation dict {summary, reasons}.

    Tries AWS Bedrock (BEDROCK_MODEL_ID from env) via the shared BedrockClient.
    On any Bedrock error (offline, access denied, model not enabled) falls back
    to a deterministic stub so enrollment is never blocked.
    """
    try:
        client = BedrockClient.from_env()
        prompt = _build_prompt(decision, bundle)
        raw_text = client.invoke(prompt, system=_SYSTEM_PROMPT)
        logger.info("bedrock_explain_ok", verdict=decision.verdict.value)

        # Extract JSON from the response (model may wrap it in prose)
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("bedrock_explain_no_json", raw=raw_text[:200])
            return _fake_explain(decision)

        result = json.loads(raw_text[start:end])
        if "summary" not in result or "reasons" not in result:
            logger.warning("bedrock_explain_missing_keys", result=result)
            return _fake_explain(decision)

        return result

    except BedrockOfflineError as exc:
        logger.warning("bedrock_offline", reason=str(exc))
        return _fake_explain(decision)
    except json.JSONDecodeError as exc:
        logger.warning("bedrock_json_decode_error", error=str(exc))
        return _fake_explain(decision)
    except Exception as exc:
        logger.error("bedrock_explain_error", error=str(exc))
        return _fake_explain(decision)
