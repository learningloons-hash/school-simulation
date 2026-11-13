"""M3 Sonnet 5.5 pin — validation and default-resolution behavior.

Covers: thinking/effort combinations that must raise *before* any HTTP request is
built, and the resolved defaults when a run specifies nothing explicit.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.config import Settings
from mirofish_backend.llm.anthropic_request import (
    SONNET_55_MODEL_ID,
    resolve_anthropic_request_config,
    validate_sonnet_55_thinking_effort,
)
from mirofish_backend.main import app


# ---------------------------------------------------------------------------
# validate_sonnet_55_thinking_effort
# ---------------------------------------------------------------------------


def test_thinking_disabled_raises_before_any_request() -> None:
    with pytest.raises(ValueError, match="disabled"):
        validate_sonnet_55_thinking_effort(
            model_id=SONNET_55_MODEL_ID,
            thinking_type="disabled",
            effort="medium",
        )


@pytest.mark.parametrize("effort", ["xhigh", "max"])
def test_between_tools_with_high_effort_raises(effort: str) -> None:
    with pytest.raises(ValueError, match="between_tools"):
        validate_sonnet_55_thinking_effort(
            model_id=SONNET_55_MODEL_ID,
            thinking_type="between_tools",
            effort=effort,
        )


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_between_tools_with_allowed_effort_passes(effort: str) -> None:
    validate_sonnet_55_thinking_effort(
        model_id=SONNET_55_MODEL_ID,
        thinking_type="between_tools",
        effort=effort,
    )


def test_non_sonnet_model_never_raises_regardless_of_combo() -> None:
    # Guardrail is Sonnet-5.5-specific; other models must not be affected.
    validate_sonnet_55_thinking_effort(
        model_id="claude-haiku-4-5-20251001",
        thinking_type="disabled",
        effort="xhigh",
    )


# ---------------------------------------------------------------------------
# Defaults: no explicit settings -> between_tools / medium
# ---------------------------------------------------------------------------


def test_sonnet_55_defaults_to_between_tools_and_medium_effort() -> None:
    cfg = resolve_anthropic_request_config(
        model_id=SONNET_55_MODEL_ID,
        settings=Settings(),
    )
    assert cfg.payload_thinking() == {"type": "between_tools"}
    assert cfg.payload_effort() == "medium"


def test_non_sonnet_model_resolves_no_thinking_or_effort() -> None:
    cfg = resolve_anthropic_request_config(
        model_id="claude-haiku-4-5-20251001",
        settings=Settings(),
    )
    assert cfg.payload_thinking() is None
    assert cfg.payload_effort() is None


# ---------------------------------------------------------------------------
# End-to-end validation surfaced as HTTP 422 before a run is even queued
# ---------------------------------------------------------------------------


@pytest.fixture
def preflight_client(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> TestClient:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "m3_validation.sqlite"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    with TestClient(app) as c:
        yield c


def _preflight_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "scenario_id": "psle_reform_mvp",
        "total_rounds": 1,
        "agent_limit": 1,
        "model_profile_id": "anthropic_sonnet_5_5",
        "llm_provider": "anthropic",
    }
    body.update(overrides)
    return body


def test_preflight_rejects_disabled_thinking(preflight_client: TestClient) -> None:
    r = preflight_client.post(
        "/simulations/preflight",
        json=_preflight_body(anthropic_thinking_type="disabled"),
    )
    assert r.status_code == 422


@pytest.mark.parametrize("effort", ["xhigh", "max"])
def test_preflight_rejects_between_tools_with_high_effort(preflight_client: TestClient, effort: str) -> None:
    r = preflight_client.post(
        "/simulations/preflight",
        json=_preflight_body(anthropic_thinking_type="between_tools", anthropic_effort=effort),
    )
    assert r.status_code == 422


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_preflight_accepts_between_tools_with_low_medium_high(preflight_client: TestClient, effort: str) -> None:
    r = preflight_client.post(
        "/simulations/preflight",
        json=_preflight_body(anthropic_thinking_type="between_tools", anthropic_effort=effort),
    )
    assert r.status_code == 200, r.text
