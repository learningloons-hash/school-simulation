"""Shared no-network HTTP mocks for M3 Sonnet 5.5 pin tests (backend/tests/test_m3_*.py).

Patches ``httpx.AsyncClient.post`` so ``claude_client`` / ``openai_compatible_client``
never make a live request; every call is captured for wire-payload assertions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

# Response text that satisfies every parser touched by the call paths under test:
# agent-turn <state>, round-end <likert>, rubric <judge_score>, and plain-text
# fallbacks for importance / reflection (which tolerate unparseable raw text).
ANTHROPIC_CANNED_TEXT = (
    "Turn narrative text.\n\n"
    "<state>\n"
    '{"support_level": 0.5, "resistance_level": 0.5, "workload_stress": 0.5, '
    '"belief_posture": "neutral", "perceived_conflict": false}\n'
    "</state>\n\n"
    "<likert>\n"
    '{"support": "somewhat support", "resistance": "moderate resistance", '
    '"workload_stress": "manageable stress"}\n'
    "</likert>\n\n"
    '<judge_score>{"score": 2, "rationale": "demonstrates understanding"}</judge_score>\n'
)


@dataclass
class CapturedRequest:
    url: str
    headers: dict[str, Any]
    json: dict[str, Any]


class _FakeHTTPResponse:
    def __init__(self, body: dict[str, Any], status_code: int = 200) -> None:
        self._body = body
        self.status_code = status_code
        self.text = json.dumps(body)

    def json(self) -> dict[str, Any]:
        return self._body


@dataclass
class FakeAnthropicTransport:
    """Stand-in for the Anthropic Messages API wire call."""

    text: str = ANTHROPIC_CANNED_TEXT
    input_tokens: int = 50
    output_tokens: int = 20
    calls: list[CapturedRequest] = field(default_factory=list)

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> _FakeHTTPResponse:
        self.calls.append(CapturedRequest(url=url, headers=dict(headers or {}), json=dict(json or {})))
        body = {
            "content": [{"type": "text", "text": self.text}],
            "usage": {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens},
        }
        return _FakeHTTPResponse(body)


@dataclass
class FakeOpenAICompatibleTransport:
    """Stand-in for an OpenAI-compatible chat/completions wire call (LM Studio / OpenAI / OpenRouter)."""

    text: str = "A plain completion."
    prompt_tokens: int = 30
    completion_tokens: int = 10
    calls: list[CapturedRequest] = field(default_factory=list)

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> _FakeHTTPResponse:
        self.calls.append(CapturedRequest(url=url, headers=dict(headers or {}), json=dict(json or {})))
        body = {
            "choices": [{"message": {"content": self.text}}],
            "usage": {"prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens},
        }
        return _FakeHTTPResponse(body)


@pytest.fixture
def anthropic_transport(monkeypatch: pytest.MonkeyPatch) -> FakeAnthropicTransport:
    transport = FakeAnthropicTransport()
    monkeypatch.setattr(httpx.AsyncClient, "post", transport.post)
    return transport


@pytest.fixture
def openai_compatible_transport(monkeypatch: pytest.MonkeyPatch) -> FakeOpenAICompatibleTransport:
    transport = FakeOpenAICompatibleTransport()
    monkeypatch.setattr(httpx.AsyncClient, "post", transport.post)
    return transport
