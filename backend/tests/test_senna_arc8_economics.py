"""Arc 8 GM follow-up — profile-aware post-run economics."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.schema import init_db
from mirofish_backend.llm.model_profiles import (
    ANTHROPIC_DEFAULT_ID,
    LOCAL_LMSTUDIO_DEFAULT_ID,
    OPENAI_DEFAULT_ID,
    OPENROUTER_DEFAULT_ID,
)
from mirofish_backend.llm.routing_policies import HEURISTIC_PROFILE_SENTINEL
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app
from mirofish_backend.simulation.economics import (
    estimated_run_cost_usd_from_transcript,
    resolve_billing_provider_key,
)


def _state_json() -> str:
    return json.dumps(
        {
            "support_level": 0.52,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
    )


async def _fake_llm(**_kwargs: object) -> LLMCompletion:
    return LLMCompletion(
        text="OK.\n\n<state>\n" + _state_json() + "\n</state>",
        input_tokens=50,
        output_tokens=10,
    )


def _wait_completed(client: TestClient, sim_id: str) -> dict:
    for _ in range(200):
        body = client.get(f"/simulations/{sim_id}").json()
        if body.get("status") == "completed":
            return body
    raise AssertionError(f"simulation {sim_id} did not complete")


def test_resolve_billing_provider_key_by_profile() -> None:
    assert (
        resolve_billing_provider_key(
            effective_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            effective_provider="lmstudio",
        )
        == "lmstudio"
    )
    assert (
        resolve_billing_provider_key(
            effective_profile_id=ANTHROPIC_DEFAULT_ID,
            effective_provider="anthropic",
        )
        == "anthropic"
    )
    assert (
        resolve_billing_provider_key(
            effective_profile_id=OPENAI_DEFAULT_ID,
            effective_provider="lmstudio",
        )
        == "openai"
    )
    assert (
        resolve_billing_provider_key(
            effective_profile_id=OPENROUTER_DEFAULT_ID,
            effective_provider="lmstudio",
        )
        == "openrouter"
    )
    assert (
        resolve_billing_provider_key(
            effective_profile_id=HEURISTIC_PROFILE_SENTINEL,
            effective_provider="heuristic",
        )
        == "lmstudio"
    )


def test_profile_aware_turn_costs() -> None:
    usage = {"input_tokens": 1_000_000, "output_tokens": 0}
    assert (
        estimated_run_cost_usd_from_transcript(
            [{"effective_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID, "effective_provider": "lmstudio", **usage}]
        )
        == 0.0
    )
    openai_cost = estimated_run_cost_usd_from_transcript(
        [{"effective_profile_id": OPENAI_DEFAULT_ID, "effective_provider": "lmstudio", **usage}]
    )
    assert openai_cost > 0
    openrouter_cost = estimated_run_cost_usd_from_transcript(
        [{"effective_profile_id": OPENROUTER_DEFAULT_ID, "effective_provider": "lmstudio", **usage}]
    )
    assert openrouter_cost > 0
    assert (
        estimated_run_cost_usd_from_transcript(
            [
                {
                    "effective_profile_id": HEURISTIC_PROFILE_SENTINEL,
                    "effective_provider": "heuristic",
                    **usage,
                }
            ]
        )
        == 0.0
    )


def test_legacy_anthropic_without_profile_id() -> None:
    cost = estimated_run_cost_usd_from_transcript(
        [{"effective_provider": "anthropic", "input_tokens": 100, "output_tokens": 20}]
    )
    assert cost == pytest.approx(0.0006, rel=1e-5)


def test_openai_default_run_economics_in_api_and_export(monkeypatch, tmp_path) -> None:
    db = tmp_path / "arc8-eco-openai.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    asyncio.run(init_db(str(db)))
    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", _fake_llm)

    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 1,
                "agent_limit": 1,
                "random_seed": 99,
                "model_profile_id": OPENAI_DEFAULT_ID,
            },
        )
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        body = _wait_completed(client, sid)
        eco = body.get("economics") or {}
        assert float(eco.get("estimated_cost_usd") or 0) > 0
        assert (body.get("transcript") or [])[0]["effective_profile_id"] == OPENAI_DEFAULT_ID

        ej = client.get(f"/simulations/{sid}/export.json")
        assert ej.status_code == 200
        run = ej.json().get("run") or {}
        assert float((run.get("economics") or {}).get("estimated_cost_usd") or 0) > 0

        zr = client.get(f"/simulations/{sid}/export.zip")
        assert zr.status_code == 200
        with zipfile.ZipFile(BytesIO(zr.content)) as zf:
            rows = list(csv.reader(io.StringIO(zf.read("agent_turns.csv").decode("utf-8"))))
        assert "effective_profile_id" in rows[0]
        assert rows[1][rows[0].index("effective_profile_id")] == OPENAI_DEFAULT_ID
