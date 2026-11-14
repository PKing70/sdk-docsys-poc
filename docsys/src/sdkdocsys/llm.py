"""Model access. Optional: without a key the pipeline still runs every deterministic check."""

from __future__ import annotations

import json
import os
import re
from typing import Protocol

DEFAULT_MODEL = "claude-sonnet-5-5"

# Running tally for this process, printed by the CLI so spend is visible, not guessed.
USAGE = {"calls": 0, "input": 0, "output": 0}


def _record(input_tokens: int, output_tokens: int) -> None:
    USAGE["calls"] += 1
    USAGE["input"] += input_tokens or 0
    USAGE["output"] += output_tokens or 0


def usage_summary() -> str:
    return (
        f"model usage this run: {USAGE['calls']} calls, "
        f"{USAGE['input']:,} input tokens, {USAGE['output']:,} output tokens"
    )


class LLM(Protocol):
    def complete(self, system: str, prompt: str, max_tokens: int = 4000) -> str: ...


class AnthropicLLM:
    def __init__(self, model: str | None = None) -> None:
        import anthropic  # optional dependency: pip install 'sdkdocsys[llm]'

        self._client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = model or os.environ.get("SDKDOCSYS_MODEL", DEFAULT_MODEL)

    def complete(self, system: str, prompt: str, max_tokens: int = 4000) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        _record(resp.usage.input_tokens, resp.usage.output_tokens)
        return "".join(b.text for b in resp.content if b.type == "text")


DEFAULT_BEDROCK_MODEL = "anthropic.claude-sonnet-4-6"


class BedrockProxyLLM:
    """Claude through a Bedrock-compatible gateway that accepts a bearer token.

    For organizations that front Bedrock with a gateway and issue short-lived tokens instead
    of API keys. Environment: ``LLM_GATEWAY_TOKEN`` and ``LLM_GATEWAY_URL`` (both required;
    the gateway base URL, to which ``/bedrock_proxy`` is appended) and ``SDKDOCSYS_MODEL``
    (default: Claude Sonnet 4.6). Needs ``pip install 'sdkdocsys[bedrock]'``.
    """

    def __init__(self, model: str | None = None, client=None) -> None:
        self.model = model or os.environ.get("SDKDOCSYS_MODEL", DEFAULT_BEDROCK_MODEL)
        if client is not None:  # injected in tests
            self._client = client
            return
        import boto3  # optional dependency

        # boto3 reads this variable as a bearer token for Bedrock.
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = os.environ["LLM_GATEWAY_TOKEN"]
        self._client = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1",
            endpoint_url=f"{os.environ['LLM_GATEWAY_URL'].rstrip('/')}/bedrock_proxy",
        )

    def complete(self, system: str, prompt: str, max_tokens: int = 4000) -> str:
        resp = self._client.converse(
            modelId=self.model,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens},
        )
        usage = resp.get("usage", {})
        _record(usage.get("inputTokens", 0), usage.get("outputTokens", 0))
        return "".join(b["text"] for b in resp["output"]["message"]["content"] if "text" in b)


def get_llm() -> LLM | None:
    """Return a model client, or ``None`` when no credentials or client library are available.

    ``LLM_GATEWAY_TOKEN`` plus ``LLM_GATEWAY_URL`` select the gateway;
    ``ANTHROPIC_API_KEY`` selects the Anthropic API.
    ``SDKDOCSYS_PROVIDER=bedrock_proxy|anthropic`` forces one when both are set.
    """
    forced = os.environ.get("SDKDOCSYS_PROVIDER")
    order = [forced] if forced else ["bedrock_proxy", "anthropic"]
    for provider in order:
        try:
            if (
                provider == "bedrock_proxy"
                and os.environ.get("LLM_GATEWAY_TOKEN")
                and os.environ.get("LLM_GATEWAY_URL")
            ):
                return BedrockProxyLLM()
            if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
                return AnthropicLLM()
        except ImportError:
            continue
    return None


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in model reply")
    return json.loads(match.group(0))


def strip_wrapping_fence(text: str) -> str:
    """Models often wrap a whole file in one fence; remove it."""
    m = re.fullmatch(r"\s*```[\w-]*\n(.*?)\n```\s*", text, re.DOTALL)
    return (m.group(1) if m else text).strip("\n") + "\n"
