"""AWS Bedrock Runtime client wrapper.

Reads credentials and config from environment variables (loaded via python-dotenv).
Exposes a single ``invoke(prompt)`` method that returns a plain-text string.

Offline mode: if ``BEDROCK_MODEL_ID`` is not set, or if ``boto3`` cannot reach
AWS (no credentials), the client raises ``BedrockOfflineError`` so callers can
fall back gracefully.
"""
from __future__ import annotations

import json
import os
from typing import Any

from shared.utils.logging import get_logger

logger = get_logger(__name__)


class BedrockOfflineError(RuntimeError):
    """Raised when Bedrock is not configured or unreachable."""


class BedrockClient:
    """Thin wrapper around boto3 bedrock-runtime.

    Usage::

        client = BedrockClient.from_env()
        text = client.invoke("Summarise this KYC evidence bundle: ...")
    """

    def __init__(
        self,
        model_id: str,
        region: str,
        max_tokens: int = 512,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ) -> None:
        self.model_id = model_id
        self.max_tokens = max_tokens
        self._client = self._build_boto_client(
            region,
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
        )

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "BedrockClient":
        """Build a BedrockClient from environment variables.

        Required env vars:
          - ``AWS_REGION`` (default: ap-south-1)
          - ``BEDROCK_MODEL_ID``

        Optional:
          - ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY``
            (if absent, boto3 uses its default credential chain:
             instance profile, ~/.aws/credentials, etc.)
          - ``AWS_SESSION_TOKEN``
          - ``BEDROCK_MAX_TOKENS`` (default: 512)
        """
        model_id = os.getenv("BEDROCK_MODEL_ID", "").strip()
        if not model_id:
            raise BedrockOfflineError(
                "BEDROCK_MODEL_ID is not set — Bedrock offline. "
                "Set it in .env or export the variable."
            )
        return cls(
            model_id=model_id,
            region=os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "ap-south-1",
            max_tokens=int(os.getenv("BEDROCK_MAX_TOKENS", "512")),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
            aws_session_token=os.getenv("AWS_SESSION_TOKEN") or None,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to the configured Bedrock model.

        Args:
            prompt: User-turn content.
            system: Optional system prompt (supported by Claude models).

        Returns:
            The model's text response as a plain string.

        Raises:
            BedrockOfflineError: On auth/endpoint failures.
            RuntimeError: On unexpected Bedrock errors.
        """
        body = self._build_request_body(prompt, system)
        try:
            response = self._client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
        except Exception as exc:  # noqa: BLE001
            _type = type(exc).__name__
            if "AccessDenied" in _type or "NoCredentials" in _type or "Endpoint" in _type:
                raise BedrockOfflineError(
                    f"Bedrock not reachable ({_type}): {exc}. "
                    "Check AWS credentials and model access in the Bedrock console."
                ) from exc
            raise RuntimeError(f"Bedrock invoke_model failed: {exc}") from exc

        raw = json.loads(response["body"].read())
        text = self._extract_text(raw)
        logger.info(
            "bedrock_invoke_ok",
            model_id=self.model_id,
            prompt_len=len(prompt),
            response_len=len(text),
        )
        return text

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_boto_client(
        self,
        region: str,
        access_key: str | None,
        secret_key: str | None,
        session_token: str | None,
    ) -> Any:
        try:
            import boto3  # type: ignore[import]
        except ImportError as exc:
            raise BedrockOfflineError("boto3 is not installed. Run: pip install boto3") from exc

        kwargs: dict[str, Any] = {"region_name": region}
        if access_key:
            kwargs["aws_access_key_id"] = access_key
        if secret_key:
            kwargs["aws_secret_access_key"] = secret_key
        if session_token:
            kwargs["aws_session_token"] = session_token

        return boto3.client("bedrock-runtime", **kwargs)

    def _build_request_body(self, prompt: str, system: str | None) -> dict[str, Any]:
        """Build model-specific request body.

        Supports Amazon Nova, Amazon Titan, and Anthropic Claude (optional).
        """
        # Amazon Nova (recommended — no company use-case form)
        if "amazon.nova" in self.model_id:
            body: dict[str, Any] = {
                "messages": [
                    {"role": "user", "content": [{"text": prompt}]},
                ],
                "inferenceConfig": {"maxTokens": self.max_tokens},
            }
            if system:
                body["system"] = [{"text": system}]
            return body

        # Amazon Titan Text
        if "amazon.titan" in self.model_id:
            return {
                "inputText": f"{system}\n\n{prompt}" if system else prompt,
                "textGenerationConfig": {"maxTokenCount": self.max_tokens},
            }

        # Anthropic Claude (requires Anthropic use-case / company form)
        if "anthropic" in self.model_id:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                body["system"] = system
            return body

        # Meta Llama / Mistral-style text completion fallback
        if "meta." in self.model_id or "mistral." in self.model_id:
            full = f"{system}\n\n{prompt}" if system else prompt
            return {
                "prompt": full,
                "max_gen_len": self.max_tokens,
                "temperature": 0.2,
            }

        # Default: Nova-style messages (safest for Amazon models)
        return {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": self.max_tokens},
        }

    def _extract_text(self, raw: dict[str, Any]) -> str:
        """Extract plain text from model-specific response shape."""
        # Amazon Nova
        if "output" in raw and isinstance(raw["output"], dict):
            message = raw["output"].get("message", {})
            content = message.get("content", [])
            parts = [p.get("text", "") for p in content if isinstance(p, dict)]
            if parts:
                return " ".join(parts).strip()

        # Anthropic Claude
        if "content" in raw and isinstance(raw["content"], list):
            parts = [p.get("text", "") for p in raw["content"] if p.get("type") == "text"]
            if parts:
                return " ".join(parts).strip()

        # Amazon Titan
        if "results" in raw:
            return raw["results"][0].get("outputText", "").strip()

        # Meta Llama
        if "generation" in raw:
            return str(raw["generation"]).strip()

        # Mistral
        if "outputs" in raw and isinstance(raw["outputs"], list):
            return str(raw["outputs"][0].get("text", "")).strip()

        # Fallback: return raw JSON string
        return json.dumps(raw)
