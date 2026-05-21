"""Senna Arc 8 iter-38 — pre-run context and cost preflight."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.config import Settings
from mirofish_backend.llm.model_profiles import (
    ANTHROPIC_DEFAULT_ID,
    LOCAL_LMSTUDIO_DEFAULT_ID,
    OPENAI_DEFAULT_ID,
    anthropic_default,
    local_lmstudio_default,
    openai_default,
    resolve_run_profiles,
)
from mirofish_backend.main import app
from mirofish_backend.simulation.economics import estimate_cost_usd
from mirofish_backend.simulation.preflight import (
    estimate_run_preflight,
    speakers_per_round_count,
)


def _settings() -> Settings:
    return Settings(
        lmstudio_base_url="http://127.0.0.1:1234/v1",
        lmstudio_model="local-test",
        anthropic_model="claude-test",
        llm_max_tokens=1024,
    )


def test_speakers_per_round_sample_k() -> None:
    assert speakers_per_round_count(agent_count=10, simulation_mode="sample_k_per_round", speakers_per_round=3) == 3
    assert speakers_per_round_count(agent_count=2, simulation_mode="sample_k_per_round", speakers_per_round=5) == 2


def test_local_only_preflight_zero_cost() -> None:
    s = _settings()
    res = resolve_run_profiles(model_profile_id=None, llm_provider="lmstudio", settings=s)
    est = estimate_run_preflight(
        total_rounds=2,
        agent_count=3,
        simulation_mode="full_round_robin",
        speakers_per_round=2,
        fidelity_tiers=[1, 1, 1],
        llm_provider="lmstudio",
        profile_resolution=res,
        llm_max_tokens=512,
        round_summary_enabled=True,
        peer_context_max_chars=1200,
        working_memory_last_k=2,
    )
    assert est.total_speaking_turns == 6
    assert est.llm_turns == 6
    assert est.heuristic_turns == 0
    assert est.estimated_cost_usd == 0.0


def test_hybrid_preflight_nonzero_cost_envelope() -> None:
    s = _settings()
    res = resolve_run_profiles(model_profile_id=None, llm_provider="hybrid", settings=s)
    est = estimate_run_preflight(
        total_rounds=2,
        agent_count=2,
        simulation_mode="full_round_robin",
        speakers_per_round=2,
        fidelity_tiers=[1, 1],
        llm_provider="hybrid",
        profile_resolution=res,
        llm_max_tokens=1024,
        round_summary_enabled=False,
        peer_context_max_chars=800,
        working_memory_last_k=2,
    )
    assert est.anthropic_llm_turns == 2
    assert est.openai_compatible_llm_turns == 2
    assert est.estimated_cost_usd > 0


def test_openai_profile_preflight_nonzero_cost() -> None:
    s = Settings(openai_model="gpt-4o-mini")
    res = resolve_run_profiles(model_profile_id=OPENAI_DEFAULT_ID, llm_provider="lmstudio", settings=s)
    est = estimate_run_preflight(
        total_rounds=1,
        agent_count=2,
        simulation_mode="full_round_robin",
        speakers_per_round=2,
        fidelity_tiers=[1, 1],
        llm_provider="lmstudio",
        profile_resolution=res,
        llm_max_tokens=512,
        round_summary_enabled=False,
        peer_context_max_chars=600,
        working_memory_last_k=2,
    )
    assert est.estimated_cost_usd > 0
    assert any("preflight:" in w for w in est.warnings)


def test_tier3_heuristic_turns_excluded_from_llm_count() -> None:
    s = _settings()
    res = resolve_run_profiles(model_profile_id=None, llm_provider="lmstudio", settings=s)
    est = estimate_run_preflight(
        total_rounds=1,
        agent_count=3,
        simulation_mode="full_round_robin",
        speakers_per_round=3,
        fidelity_tiers=[1, 2, 3],
        llm_provider="lmstudio",
        profile_resolution=res,
        llm_max_tokens=512,
        round_summary_enabled=False,
        peer_context_max_chars=600,
        working_memory_last_k=2,
    )
    assert est.llm_turns == 2
    assert est.heuristic_turns == 1


def test_unknown_context_window_warning() -> None:
    s = _settings()
    res = resolve_run_profiles(model_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID, llm_provider="lmstudio", settings=s)
    est = estimate_run_preflight(
        total_rounds=3,
        agent_count=2,
        simulation_mode="full_round_robin",
        speakers_per_round=2,
        fidelity_tiers=[1, 1],
        llm_provider="lmstudio",
        profile_resolution=res,
        llm_max_tokens=512,
        round_summary_enabled=True,
        peer_context_max_chars=1200,
        working_memory_last_k=2,
    )
    assert est.context_window is None
    assert any("context window is unknown" in w for w in est.warnings)


def test_economics_openai_pricing_key_nonzero() -> None:
    c = estimate_cost_usd(input_tokens=1_000_000, output_tokens=1_000_000, provider_key="openai")
    assert c > 0


@pytest.fixture
def client_preflight(monkeypatch, tmp_path):
    db = tmp_path / "preflight.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as c:
        yield c


def test_post_preflight_endpoint_local_zero_cost(client_preflight: TestClient) -> None:
    r = client_preflight.post(
        "/simulations/preflight",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 2,
            "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["preflight"]["estimated_cost_usd"] == 0
    assert body["preflight"]["llm_turns"] == 2


def test_post_preflight_hybrid_nonzero(client_preflight: TestClient) -> None:
    r = client_preflight.post(
        "/simulations/preflight",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 2,
            "agent_limit": 2,
            "llm_provider": "hybrid",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["preflight"]["estimated_cost_usd"] > 0


@pytest.mark.asyncio
async def test_queue_run_includes_preflight_warnings(tmp_path) -> None:
    from mirofish_backend.api import simulations as sim_api
    from mirofish_backend.api.simulations import SimulationRunRequest, queue_simulation_run

    settings = Settings(sqlite_path=str(tmp_path / "q.sqlite"), llm_provider="hybrid")
    captured: dict[str, object] = {}

    async def fake_create(*_a, config_snapshot=None, **kwargs):
        captured["config_snapshot"] = config_snapshot
        return "sim-preflight"

    async def noop_guarded(**_kwargs):
        return None

    def _discard(coro, *_a, **_kw):
        if asyncio.iscoroutine(coro):
            coro.close()

    with (
        patch.object(sim_api, "create_simulation_run", side_effect=fake_create),
        patch.object(sim_api, "run_simulation_task_guarded", side_effect=noop_guarded),
        patch.object(sim_api, "load_scenario_for_run") as load_sc,
        patch.object(sim_api.asyncio, "create_task", side_effect=_discard),
    ):
        from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig

        sc = ScenarioConfig(
            scenario_id="psle_reform_mvp",
            name="T",
            policy_events={1: "p"},
            personas=[
                PersonaTemplate(
                    persona_id="a",
                    role="lead",
                    name="A",
                    role_level=1,
                    style_cues="n",
                    beliefs={},
                )
            ],
        )
        load_sc.return_value = (sc, "builtin")
        resp = await queue_simulation_run(
            settings,
            SimulationRunRequest(
                scenario_id="psle_reform_mvp",
                total_rounds=1,
                agent_limit=1,
                llm_provider="hybrid",
            ),
        )

    snap = captured.get("config_snapshot")
    assert isinstance(snap, dict)
    pf = snap.get("preflight")
    assert isinstance(pf, dict)
    assert pf.get("llm_turns") == 1
    assert any("preflight:" in w for w in resp.warnings)
