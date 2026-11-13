"""M3 Sonnet 5.5 pin — run_manifest fields recorded on config_snapshot at queue time."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.llm.anthropic_request import sonnet_55_max_tokens_manifest
from mirofish_backend.llm.model_profiles import ANTHROPIC_SONNET_55_ID
from mirofish_backend.main import app
from sonnet55_test_support import (  # noqa: F401 -- fixture referenced by name in test signatures
    FakeAnthropicTransport,
    anthropic_transport,
)

SONNET_55 = "claude-sonnet-5-5"


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, anthropic_transport: FakeAnthropicTransport
) -> TestClient:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "m3_manifest.sqlite"))
    monkeypatch.setenv("TRANSCRIPT_DIR", str(tmp_path / "transcripts"))
    with TestClient(app) as c:
        yield c


def test_run_manifest_records_model_thinking_effort_price_and_floors(client: TestClient) -> None:
    r = client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 7,
            "model_profile_id": ANTHROPIC_SONNET_55_ID,
            "llm_provider": "anthropic",
        },
    )
    assert r.status_code == 200, r.text
    sim_id = r.json()["id"]

    status = client.get(f"/simulations/{sim_id}")
    assert status.status_code == 200
    snapshot = status.json()["config_snapshot"]
    manifest = snapshot["run_manifest"]

    assert manifest["resolved_model_id"] == SONNET_55
    assert manifest["thinking"] == {"type": "between_tools"}
    assert manifest["effort"] == "medium"
    assert manifest["price_map_date"] == "2026-11-12"
    assert manifest["price_map_key"] == "anthropic_sonnet_5_5"
    assert manifest["sonnet_55_max_tokens_floors"] == sonnet_55_max_tokens_manifest()


def test_run_manifest_omits_floors_block_for_non_sonnet_model(client: TestClient) -> None:
    r = client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 8,
            "model_profile_id": "anthropic_default",
            "llm_provider": "anthropic",
        },
    )
    assert r.status_code == 200, r.text
    sim_id = r.json()["id"]

    status = client.get(f"/simulations/{sim_id}")
    manifest = status.json()["config_snapshot"]["run_manifest"]
    assert "sonnet_55_max_tokens_floors" not in manifest
    assert manifest["thinking"] is None
    assert manifest["effort"] is None
