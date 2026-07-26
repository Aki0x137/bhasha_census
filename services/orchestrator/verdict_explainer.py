"""Bedrock-backed enrollment verdict explainer.

Generates a structured JSON explanation of the verdict.
LLM is NOT the final authority — policy verdict is deterministic.
Bedrock merely provides a human-readable summary bound to the evidence.
"""
from __future__ import annotations

import json
import os

from shared.schemas.decision import EnrollmentDecision
from shared.schemas.evidence_bundle import EvidenceBundle
from shared.utils.logging import get_logger

logger = get_logger(__name__)

# Use the configured model. In ap-south-1 the plain on-demand id
# (amazon.nova-lite-v1:0) raises ValidationException — the APAC inference profile
# (apac.amazon.nova-*) is required, which is what .env / BEDROCK_MODEL_ID carries.
_BEDROCK_MODEL = os.getenv("BEDROCK_MODEL_ID") or "apac.amazon.nova-lite-v1:0"
_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"


def _build_prompt(decision: EnrollmentDecision, bundle: EvidenceBundle) -> str:
    return f"""You are a census enrollment assistant. Summarize the enrollment outcome in JSON.
Output ONLY a JSON object with keys: "summary" (1-2 sentences), "reasons" (list of strings).
Do NOT invent facts not present in the evidence. Do NOT override the verdict.

Verdict: {decision.verdict.value}
Confidence: {decision.confidence}
Reason codes: {', '.join(decision.reason_codes)}
Evidence scores: {json.dumps(decision.evidence_summary)}

Respond with valid JSON only."""


def _call_bedrock(prompt: str) -> dict:
    import boto3
    import json

    bedrock = boto3.client("bedrock-runtime", region_name=_REGION)
    body = json.dumps({
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": 256, "temperature": 0.1},
    })
    resp = bedrock.invoke_model(modelId=_BEDROCK_MODEL, body=body)
    raw = json.loads(resp["body"].read())
    text = raw["output"]["message"]["content"][0]["text"]
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


def _fake_explain(decision: EnrollmentDecision) -> dict:
    return {
        "summary": f"Enrollment {decision.verdict.value} with confidence {decision.confidence:.0%}.",
        "reasons": decision.reason_codes,
    }


def explain_verdict(decision: EnrollmentDecision, bundle: EvidenceBundle) -> dict:
    """Return a structured explanation dict {summary, reasons}."""
    # Bedrock is reachable via either traditional IAM keys or a Bedrock bearer
    # token (AWS_BEARER_TOKEN_BEDROCK, picked up automatically by boto3). Gating
    # only on AWS_ACCESS_KEY_ID silently forced fake mode for bearer-token setups.
    if not (os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_BEARER_TOKEN_BEDROCK")):
        logger.warning("bedrock_fake_mode", reason="no AWS credentials or bearer token set")
        return _fake_explain(decision)

    try:
        prompt = _build_prompt(decision, bundle)
        result = _call_bedrock(prompt)
        # Guarantee required keys
        if "summary" not in result or "reasons" not in result:
            return _fake_explain(decision)
        return result
    except Exception as exc:
        logger.error("bedrock_explain_error", error=str(exc))
        return _fake_explain(decision)
