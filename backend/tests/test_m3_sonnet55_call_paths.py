"""M3 Sonnet 5.5 pin — every non-simulation Anthropic tooling call path.

Each test calls the real production entry point (no mocking of our own code,
only of the HTTP transport) and asserts that the wire payload actually sent to
`POST https://api.anthropic.com/v1/messages` carries `thinking` and
`output_config.effort` when (and only when) the model is Sonnet 5.5.

Agent-turn / Likert / importance / reflection call sites live in
``test_m3_sonnet55_simulation_paths.py`` since they require simulation context.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException

from senna_backend.agent.orchestrator import llm_build_execution_plan
from senna_backend.api.scenario_catalog import LlmFillRequest, llm_fill_persona_sections
from senna_backend.api.scenarios_generate import GenerateFromBriefRequest, generate_scenario_from_brief
from senna_backend.api.simulations import SimulationAnalyzeRequest, analyze_simulation_export
from senna_backend.config import Settings, get_settings
from senna_backend.diagnostics.architectural_interview import score_interview_response
from senna_backend.llm.model_profiles import ANTHROPIC_SONNET_55_ID
from senna_backend.llm.router import llm_complete
from sonnet55_test_support import (  # noqa: F401 -- fixtures referenced by name in test signatures
    CapturedRequest,
    FakeAnthropicTransport,
    FakeOpenAICompatibleTransport,
    anthropic_transport,
    openai_compatible_transport,
)

SONNET_55 = "claude-sonnet-5-5"


def _wire_effort(payload: dict[str, object]) -> str | None:
    cfg = payload.get("output_config")
    return cfg.get("effort") if isinstance(cfg, dict) else None


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_sends_thinking_and_effort_for_sonnet_55(
    monkeypatch: pytest.MonkeyPatch, anthropic_transport: FakeAnthropicTransport
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    monkeypatch.setenv("ANTHROPIC_MODEL", SONNET_55)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    async def _fake_bundle(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "run": {"status": "completed"},
            "transcript": [],
            "outcome_indicators": [],
            "state_timeline": [],
            "validity_notes": [],
        }

    monkeypatch.setattr(
        "senna_backend.api.simulations.get_simulation_export_bundle",
        _fake_bundle,
    )

    await analyze_simulation_export(
        simulation_id="sim-1",
        body=SimulationAnalyzeRequest(research_question="What drove the outcome?"),
    )

    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["model"] == SONNET_55
    assert payload["thinking"] == {"type": "between_tools"}
    assert _wire_effort(payload) == "medium"


# ---------------------------------------------------------------------------
# agent plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_plan_sends_thinking_and_effort_for_sonnet_55(
    anthropic_transport: FakeAnthropicTransport,
) -> None:
    settings = Settings(llm_provider="anthropic", anthropic_model=SONNET_55, anthropic_api_key="sk-test-fake")
    try:
        await llm_build_execution_plan(settings, question="Simulate a school policy rollout.")
    except Exception:
        pass  # planner-JSON parsing is irrelevant to this test; the wire call already happened

    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["model"] == SONNET_55
    assert payload["thinking"] == {"type": "between_tools"}
    assert _wire_effort(payload) == "medium"


@pytest.mark.asyncio
async def test_agent_plan_sends_thinking_and_effort_via_env_var_override(
    monkeypatch: pytest.MonkeyPatch, anthropic_transport: FakeAnthropicTransport
) -> None:
    """Global ANTHROPIC_MODEL env var path, not an explicit model kwarg."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    monkeypatch.setenv("ANTHROPIC_MODEL", SONNET_55)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    settings = get_settings()
    assert settings.anthropic_model == SONNET_55
    assert settings.llm_provider == "anthropic"

    try:
        await llm_build_execution_plan(settings, question="Simulate a school policy rollout.")
    except Exception:
        pass

    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["model"] == SONNET_55
    assert "thinking" in payload
    assert "output_config" in payload


# ---------------------------------------------------------------------------
# scenario LLM fill
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_llm_fill_sends_thinking_and_effort_for_sonnet_55(
    monkeypatch: pytest.MonkeyPatch, anthropic_transport: FakeAnthropicTransport
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    monkeypatch.setenv("ANTHROPIC_MODEL", SONNET_55)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    await llm_fill_persona_sections(
        scenario_id="psle_reform_mvp",
        body=LlmFillRequest(persona_id="agent_a", role="teacher"),
    )

    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["model"] == SONNET_55
    assert payload["thinking"] == {"type": "between_tools"}
    assert _wire_effort(payload) == "medium"


# ---------------------------------------------------------------------------
# scenario generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_generate_sends_thinking_and_effort_for_sonnet_55(
    monkeypatch: pytest.MonkeyPatch, anthropic_transport: FakeAnthropicTransport
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    monkeypatch.setenv("ANTHROPIC_MODEL", SONNET_55)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    with pytest.raises(HTTPException):
        # The canned transport text is not a scenario JSON document, so the
        # endpoint itself 422s -- irrelevant here; the wire call already fired.
        await generate_scenario_from_brief(
            GenerateFromBriefRequest(brief="A mid-sized primary school rolls out a new streaming policy.")
        )

    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["model"] == SONNET_55
    assert payload["thinking"] == {"type": "between_tools"}
    assert _wire_effort(payload) == "medium"


# ---------------------------------------------------------------------------
# architectural-interview rubric judge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_architectural_interview_rubric_sends_thinking_and_effort_for_sonnet_55(
    monkeypatch: pytest.MonkeyPatch, anthropic_transport: FakeAnthropicTransport
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    settings = Settings(anthropic_model=SONNET_55, anthropic_api_key="sk-test-fake")

    await score_interview_response(
        category="identity",
        question_text="How does this change your view?",
        response_text="It made me reconsider my assumptions about rollout pace.",
        judge_profile_id=ANTHROPIC_SONNET_55_ID,
        temperature=0.0,
        max_tokens=256,
        settings=settings,
        rubric_excerpt="Score 0 (inadequate) to 2 (adequate).",
    )

    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["model"] == SONNET_55
    assert payload["thinking"] == {"type": "between_tools"}
    assert _wire_effort(payload) == "medium"


# ---------------------------------------------------------------------------
# Non-Sonnet models: no thinking / output_config, max_tokens unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_haiku_payload_has_no_thinking_or_effort_and_max_tokens_unchanged(
    anthropic_transport: FakeAnthropicTransport,
) -> None:
    await llm_complete(
        provider="anthropic",
        messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
        temperature=0.0,
        max_tokens=77,
        lmstudio_base_url="http://127.0.0.1:9",
        lmstudio_model="unused",
        anthropic_api_key="sk-test-fake",
        anthropic_model="claude-haiku-4-5-20251001",
        llm_call_site="agent_turn",  # even a Sonnet-floored call site must not affect Haiku
    )
    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert "thinking" not in payload
    assert "output_config" not in payload
    assert payload["max_tokens"] == 77


@pytest.mark.asyncio
async def test_openai_compatible_payload_has_no_thinking_or_effort_and_max_tokens_unchanged(
    openai_compatible_transport: FakeOpenAICompatibleTransport,
) -> None:
    await llm_complete(
        provider="lmstudio",
        messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
        temperature=0.0,
        max_tokens=77,
        lmstudio_base_url="http://127.0.0.1:9/v1",
        lmstudio_model="some-local-model",
        anthropic_api_key="",
        anthropic_model="unused",
        llm_call_site="agent_turn",
    )
    assert len(openai_compatible_transport.calls) == 1
    payload = openai_compatible_transport.calls[0].json
    assert "thinking" not in payload
    assert "output_config" not in payload
    assert payload["max_tokens"] == 77


# ---------------------------------------------------------------------------
# Response parsing: thinking blocks are stripped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_thinking_content_blocks_are_stripped_from_parsed_response(
    monkeypatch: pytest.MonkeyPatch, anthropic_transport: FakeAnthropicTransport
) -> None:
    class _MixedBlockResponse:
        status_code = 200
        text = "{}"

        def json(self) -> dict[str, object]:
            return {
                "content": [
                    {"type": "thinking", "thinking": "Let me work through this step by step..."},
                    {"type": "text", "text": "Final answer only."},
                ],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }

    async def _post(self: object, url: str, *, headers: object = None, json: object = None) -> object:
        anthropic_transport.calls.append(
            CapturedRequest(url=url, headers=dict(headers or {}), json=dict(json or {}))
        )
        return _MixedBlockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", _post)

    completion = await llm_complete(
        provider="anthropic",
        messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
        temperature=0.0,
        max_tokens=512,
        lmstudio_base_url="http://127.0.0.1:9",
        lmstudio_model="unused",
        anthropic_api_key="sk-test-fake",
        anthropic_model=SONNET_55,
        llm_call_site="agent_turn",
    )
    assert completion.text == "Final answer only."
    assert "Let me work through" not in completion.text
