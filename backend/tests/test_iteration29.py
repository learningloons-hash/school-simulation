"""Iteration 29 — run economics: token columns, totals, estimated cost, API + export."""

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
from mirofish_backend.export_bundle import EXPORT_VERSION
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app
from mirofish_backend.simulation.economics import (
    build_run_economics_payload,
    estimate_cost_usd,
    estimated_run_cost_usd_from_transcript,
    tier_breakdown_from_transcript,
)


@pytest.fixture
def client_i29(monkeypatch, tmp_path):
    db = tmp_path / "i29.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))

    async def fake_llm(**_kwargs: object) -> LLMCompletion:
        state = {
            "support_level": 0.52,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return LLMCompletion(
            text="OK.\n\n<state>\n" + json.dumps(state) + "\n</state>",
            input_tokens=100,
            output_tokens=20,
        )

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm)

    with TestClient(app) as c:
        yield c


def test_get_simulation_includes_economics_and_turn_tokens(client_i29: TestClient) -> None:
    r = client_i29.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 2,
            "random_seed": 1,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    for _ in range(200):
        st = client_i29.get(f"/simulations/{sid}")
        assert st.status_code == 200
        if st.json().get("status") == "completed":
            break
    else:
        raise AssertionError("run did not complete")

    body = client_i29.get(f"/simulations/{sid}").json()
    eco = body.get("economics") or {}
    assert eco.get("total_input_tokens") == 200
    assert eco.get("total_output_tokens") == 40
    assert eco.get("tier_breakdown", {}).get("tier_1_turns") == 2
    turns = body.get("transcript") or []
    assert all(t.get("input_tokens") == 100 for t in turns)
    assert all(t.get("output_tokens") == 20 for t in turns)


def test_export_json_run_has_economics_and_export_version(client_i29: TestClient) -> None:
    r = client_i29.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 2,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    for _ in range(200):
        if client_i29.get(f"/simulations/{sid}").json().get("status") == "completed":
            break
    else:
        raise AssertionError("timeout")

    ej = client_i29.get(f"/simulations/{sid}/export.json")
    assert ej.status_code == 200
    payload = ej.json()
    assert payload.get("export_version") == EXPORT_VERSION
    assert EXPORT_VERSION == "9"
    run = payload.get("run") or {}
    assert "economics" in run
    assert run["economics"].get("total_input_tokens") == 100


def test_experiment_detail_has_total_estimated_cost_and_comparison_csv_columns(client_i29: TestClient) -> None:
    r = client_i29.post(
        "/experiments",
        json={
            "name": "econ test",
            "scenario_id": "psle_reform_mvp",
            "random_seed": 3,
            "total_rounds": 1,
            "agent_limit": 2,
            "runs": [{"label": "only", "sampling_strategy": "full_census"}],
        },
    )
    assert r.status_code == 200, r.text
    exp_id = r.json()["experiment_id"]
    for _ in range(300):
        d = client_i29.get(f"/experiments/{exp_id}").json()
        if d.get("experiment", {}).get("status") == "completed":
            break
    else:
        raise AssertionError("experiment did not complete")

    detail = client_i29.get(f"/experiments/{exp_id}").json()
    assert "total_estimated_cost_usd" in detail
    assert detail["total_estimated_cost_usd"] == 0.0
    run0 = (detail.get("runs") or [{}])[0]
    assert run0.get("economics", {}).get("total_input_tokens") == 200

    zr = client_i29.get(f"/experiments/{exp_id}/export.zip")
    assert zr.status_code == 200
    with zipfile.ZipFile(BytesIO(zr.content)) as zf:
        raw = zf.read("comparison.csv").decode("utf-8")
    rows = list(csv.reader(io.StringIO(raw)))
    header = rows[0]
    assert "input_tokens" in header and "estimated_cost_usd" in header


def test_get_simulation_anthropic_provider_positive_estimated_cost(monkeypatch, tmp_path) -> None:
    """Architect review M5: exercise non-zero pricing path (per-turn ``effective_provider`` = anthropic)."""
    db = tmp_path / "i29_anthropic.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    asyncio.run(init_db(str(db)))

    async def fake_llm(**_kwargs: object) -> LLMCompletion:
        state = {
            "support_level": 0.52,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return LLMCompletion(
            text="OK.\n\n<state>\n" + json.dumps(state) + "\n</state>",
            input_tokens=100,
            output_tokens=20,
        )

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm)

    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 1,
                "agent_limit": 2,
                "random_seed": 99,
                "llm_provider": "anthropic",
            },
        )
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        for _ in range(200):
            st = client.get(f"/simulations/{sid}").json()
            if st.get("status") == "completed":
                break
        else:
            raise AssertionError("run did not complete")
        eco = st.get("economics") or {}
    # 2 turns × (100 in @ $3/M + 20 out @ $15/M) = 2 × 0.0006 = 0.0012
    assert float(eco.get("estimated_cost_usd") or 0) == pytest.approx(0.0012, rel=1e-5)
    assert eco.get("total_input_tokens") == 200
    assert eco.get("total_output_tokens") == 40


def test_economics_pure_functions() -> None:
    """Architect review M3: direct coverage of ``economics.py`` helpers."""
    assert estimate_cost_usd(input_tokens=1_000_000, output_tokens=0, provider_key="lmstudio") == 0.0
    assert estimate_cost_usd(input_tokens=1_000_000, output_tokens=0, provider_key="anthropic") == 3.0
    assert estimate_cost_usd(input_tokens=1_000_000, output_tokens=1_000_000, provider_key="hybrid") == pytest.approx(
        3.0 + 15.0, rel=1e-9
    )
    # Unknown provider_key → _per_mtok_rates falls back to anthropic defaults
    assert estimate_cost_usd(input_tokens=1_000_000, output_tokens=0, provider_key="future_vendor") == 3.0

    assert estimated_run_cost_usd_from_transcript([]) == 0.0
    assert (
        estimated_run_cost_usd_from_transcript(
            [
                {
                    "effective_provider": "anthropic",
                    "effective_profile_id": "anthropic_default",
                    "input_tokens": 100,
                    "output_tokens": 20,
                }
            ]
        )
        == pytest.approx(0.0006, rel=1e-5)
    )
    assert (
        estimated_run_cost_usd_from_transcript(
            [{"effective_provider": "anthropic", "input_tokens": 100, "output_tokens": 20}]
        )
        == pytest.approx(0.0006, rel=1e-5)
    )
    assert (
        estimated_run_cost_usd_from_transcript(
            [{"effective_provider": "anthropic", "input_tokens": None, "output_tokens": 20}]
        )
        == 0.0
    )

    tb = tier_breakdown_from_transcript(
        [
            {"fidelity_tier": 1},
            {"fidelity_tier": 2},
            {"fidelity_tier": 3},
            {"fidelity_tier": "oops"},
        ]
    )
    assert tb["tier_1_turns"] == 2  # invalid coerces to 1
    assert tb["tier_2_turns"] == 1
    assert tb["tier_3_turns"] == 1

    payload = build_run_economics_payload(
        [{"fidelity_tier": 1, "effective_provider": "anthropic", "input_tokens": 100, "output_tokens": 20}],
        total_input_tokens=100,
        total_output_tokens=20,
        llm_provider="anthropic",
    )
    assert payload["estimated_cost_usd"] == pytest.approx(0.0006, rel=1e-5)
    assert payload["llm_provider"] == "anthropic"
