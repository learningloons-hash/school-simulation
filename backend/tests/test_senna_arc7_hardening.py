"""Senna Arc 7 iter-34 — compatibility, export provenance, and migration hardening."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import zipfile
from io import BytesIO
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.config import Settings
from mirofish_backend.db.schema import init_db
from mirofish_backend.export_bundle import EXPORT_VERSION
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID, LOCAL_LMSTUDIO_DEFAULT_ID
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app


def _minimal_scenario():
    from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig

    return ScenarioConfig(
        scenario_id="psle_reform_mvp",
        name="Test",
        policy_events={1: "policy"},
        personas=[
            PersonaTemplate(
                persona_id="agent_a",
                role="lead",
                name="Agent A",
                role_level=1,
                style_cues="neutral",
                beliefs={},
            )
        ],
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


def _discard_create_task(coro: object, *_args: object, **_kwargs: object) -> None:
    """Synchronous stand-in for asyncio.create_task — close coroutine to avoid ResourceWarning."""
    if asyncio.iscoroutine(coro):
        coro.close()
    return None


async def _fake_llm(**_kwargs: object) -> LLMCompletion:
    return LLMCompletion(
        text="OK.\n\n<state>\n" + _state_json() + "\n</state>",
        input_tokens=50,
        output_tokens=10,
    )


def _wait_completed(client: TestClient, sim_id: str, *, max_poll: int = 200) -> dict[str, Any]:
    for _ in range(max_poll):
        body = client.get(f"/simulations/{sim_id}").json()
        if body.get("status") == "completed":
            return body
    raise AssertionError(f"simulation {sim_id} did not complete")


def _assert_arc7_config_snapshot(snap: dict[str, Any], *, llm_provider: str) -> None:
    assert snap.get("llm_provider") == llm_provider
    assert snap.get("routing_policy") is not None
    assert snap.get("routing_profile_local_id") == LOCAL_LMSTUDIO_DEFAULT_ID
    assert snap.get("routing_profile_frontier_id") == ANTHROPIC_DEFAULT_ID
    if llm_provider == "hybrid":
        assert snap.get("routing_policy") == "hybrid_first_turn"
        assert snap.get("model_profile") is None
        assert isinstance(snap.get("model_profile_local"), dict)
        assert isinstance(snap.get("model_profile_frontier"), dict)
    elif llm_provider == "anthropic":
        assert snap.get("routing_policy") == "frontier_only"
        assert (snap.get("model_profile") or {}).get("profile_id") == ANTHROPIC_DEFAULT_ID
    else:
        assert snap.get("routing_policy") == "local_only"
        mp = snap.get("model_profile")
        if mp is not None:
            assert mp.get("profile_id") in (LOCAL_LMSTUDIO_DEFAULT_ID, None)


def _assert_export_provenance(client: TestClient, sim_id: str) -> None:
    status = _wait_completed(client, sim_id)
    assert status.get("economics") is not None
    assert status["economics"].get("total_input_tokens") is not None

    turns = status.get("transcript") or []
    assert turns
    t0 = turns[0]
    assert t0.get("effective_provider")
    assert t0.get("effective_model")
    assert t0.get("effective_profile_id")
    assert t0.get("input_tokens") is not None
    assert t0.get("output_tokens") is not None

    ej = client.get(f"/simulations/{sim_id}/export.json")
    assert ej.status_code == 200
    payload = ej.json()
    assert payload.get("export_version") == EXPORT_VERSION
    run = payload.get("run") or {}
    cfg = run.get("config_snapshot") or {}
    assert cfg.get("routing_policy")
    assert cfg.get("routing_profile_local_id")
    assert "economics" in run
    ex_turns = payload.get("transcript") or []
    assert ex_turns[0].get("effective_provider") == t0.get("effective_provider")

    zr = client.get(f"/simulations/{sim_id}/export.zip")
    assert zr.status_code == 200
    with zipfile.ZipFile(BytesIO(zr.content)) as zf:
        raw = zf.read("agent_turns.csv").decode("utf-8")
    rows = list(csv.reader(io.StringIO(raw)))
    header = rows[0]
    assert "effective_provider" in header
    assert "effective_model" in header
    assert "effective_profile_id" in header
    assert "input_tokens" in header
    assert "output_tokens" in header


@pytest.fixture
def client_arc7(monkeypatch, tmp_path):
    db = tmp_path / "arc7.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))
    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", _fake_llm)
    with TestClient(app) as c:
        yield c


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("request_kwargs", "expected_llm_provider", "expected_routing_policy"),
    [
        ({}, "lmstudio", "local_only"),
        ({"llm_provider": "lmstudio"}, "lmstudio", "local_only"),
        ({"llm_provider": "anthropic"}, "anthropic", "frontier_only"),
        ({"llm_provider": "hybrid"}, "hybrid", "hybrid_first_turn"),
        (
            {"model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID},
            "lmstudio",
            "local_only",
        ),
        (
            {"model_profile_id": ANTHROPIC_DEFAULT_ID},
            "anthropic",
            "frontier_only",
        ),
        (
            {"model_profile_id": ANTHROPIC_DEFAULT_ID, "llm_provider": "anthropic"},
            "anthropic",
            "frontier_only",
        ),
    ],
)
async def test_queue_run_request_shapes_persist_arc7_metadata(
    tmp_path,
    request_kwargs: dict[str, Any],
    expected_llm_provider: str,
    expected_routing_policy: str,
) -> None:
    from mirofish_backend.api import simulations as sim_api
    from mirofish_backend.api.simulations import SimulationRunRequest, queue_simulation_run

    settings = Settings(
        sqlite_path=str(tmp_path / "q.sqlite"),
        llm_provider="lmstudio",
        lmstudio_model="local-default-model",
        anthropic_model="claude-default",
    )
    created: dict[str, object] = {}

    async def fake_create(*_a, config_snapshot=None, **kwargs):
        created["config_snapshot"] = config_snapshot
        return "sim-compat"

    async def noop_guarded(**_kwargs):
        return None

    with (
        patch.object(sim_api, "create_simulation_run", side_effect=fake_create),
        patch.object(sim_api, "run_simulation_task_guarded", side_effect=noop_guarded),
        patch.object(sim_api, "load_scenario_for_run", return_value=(_minimal_scenario(), "builtin")),
        patch.object(sim_api.asyncio, "create_task", side_effect=_discard_create_task),
    ):
        req = SimulationRunRequest(scenario_id="psle_reform_mvp", **request_kwargs)
        await queue_simulation_run(settings, req)

    snap = created.get("config_snapshot")
    assert isinstance(snap, dict)
    assert snap.get("llm_provider") == expected_llm_provider
    assert snap.get("routing_policy") == expected_routing_policy
    _assert_arc7_config_snapshot(snap, llm_provider=expected_llm_provider)


def test_post_run_omitted_llm_provider_uses_server_default(client_arc7: TestClient) -> None:
    r = client_arc7.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 7,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    body = _wait_completed(client_arc7, sid)
    cfg = (body.get("config_snapshot") or {})
    assert cfg.get("llm_provider") == "lmstudio"
    _assert_export_provenance(client_arc7, sid)


@pytest.mark.asyncio
async def test_queue_anthropic_profile_only_overrides_server_default_lmstudio(tmp_path) -> None:
    from mirofish_backend.api import simulations as sim_api
    from mirofish_backend.api.simulations import SimulationRunRequest, queue_simulation_run

    settings = Settings(
        sqlite_path=str(tmp_path / "anthropic-only.sqlite"),
        llm_provider="lmstudio",
    )
    created: dict[str, object] = {}

    async def fake_create(*_a, config_snapshot=None, **kwargs):
        created["config_snapshot"] = config_snapshot
        return "sim-anthropic-inferred"

    async def noop_guarded(**_kwargs):
        return None

    with (
        patch.object(sim_api, "create_simulation_run", side_effect=fake_create),
        patch.object(sim_api, "run_simulation_task_guarded", side_effect=noop_guarded),
        patch.object(sim_api, "load_scenario_for_run", return_value=(_minimal_scenario(), "builtin")),
        patch.object(sim_api.asyncio, "create_task", side_effect=_discard_create_task),
    ):
        await queue_simulation_run(
            settings,
            SimulationRunRequest(
                scenario_id="psle_reform_mvp",
                model_profile_id=ANTHROPIC_DEFAULT_ID,
            ),
        )

    snap = created.get("config_snapshot")
    assert isinstance(snap, dict)
    assert snap.get("llm_provider") == "anthropic"
    assert snap.get("routing_policy") == "frontier_only"


@pytest.mark.asyncio
async def test_queue_explicit_llm_provider_wins_over_profile_id(tmp_path) -> None:
    from mirofish_backend.api import simulations as sim_api
    from mirofish_backend.api.simulations import SimulationRunRequest, queue_simulation_run

    settings = Settings(sqlite_path=str(tmp_path / "explicit-wins.sqlite"), llm_provider="hybrid")
    created: dict[str, object] = {}

    async def fake_create(*_a, config_snapshot=None, **kwargs):
        created["config_snapshot"] = config_snapshot
        return "sim-explicit-wins"

    async def noop_guarded(**_kwargs):
        return None

    with (
        patch.object(sim_api, "create_simulation_run", side_effect=fake_create),
        patch.object(sim_api, "run_simulation_task_guarded", side_effect=noop_guarded),
        patch.object(sim_api, "load_scenario_for_run", return_value=(_minimal_scenario(), "builtin")),
        patch.object(sim_api.asyncio, "create_task", side_effect=_discard_create_task),
    ):
        await queue_simulation_run(
            settings,
            SimulationRunRequest(
                scenario_id="psle_reform_mvp",
                model_profile_id=ANTHROPIC_DEFAULT_ID,
                llm_provider="lmstudio",
            ),
        )

    snap = created.get("config_snapshot")
    assert isinstance(snap, dict)
    assert snap.get("llm_provider") == "lmstudio"
    assert snap.get("routing_policy") == "local_only"


def test_resolve_run_llm_provider_inference() -> None:
    from mirofish_backend.llm.model_profiles import resolve_run_llm_provider

    s = Settings(llm_provider="lmstudio")
    assert (
        resolve_run_llm_provider(
            request_llm_provider=None,
            model_profile_id=ANTHROPIC_DEFAULT_ID,
            settings=s,
        )
        == "anthropic"
    )
    assert (
        resolve_run_llm_provider(
            request_llm_provider=None,
            model_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            settings=s,
        )
        == "lmstudio"
    )
    assert (
        resolve_run_llm_provider(
            request_llm_provider="hybrid",
            model_profile_id=ANTHROPIC_DEFAULT_ID,
            settings=s,
        )
        == "hybrid"
    )
    assert (
        resolve_run_llm_provider(
            request_llm_provider=None,
            model_profile_id=None,
            settings=s,
        )
        == "lmstudio"
    )


def test_post_run_anthropic_profile_only_infers_provider(monkeypatch, tmp_path) -> None:
    db = tmp_path / "arc7-anthropic-infer.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    asyncio.run(init_db(str(db)))
    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", _fake_llm)

    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 1,
                "agent_limit": 1,
                "random_seed": 11,
                "model_profile_id": ANTHROPIC_DEFAULT_ID,
            },
        )
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        body = _wait_completed(client, sid)
        cfg = body.get("config_snapshot") or {}
        assert cfg.get("llm_provider") == "anthropic"
        assert cfg.get("routing_policy") == "frontier_only"
        turns = body.get("transcript") or []
        assert turns[0]["effective_provider"] == "anthropic"
        assert turns[0]["effective_profile_id"] == ANTHROPIC_DEFAULT_ID


def test_post_run_local_profile_id_default_path(client_arc7: TestClient) -> None:
    r = client_arc7.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 8,
            "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    body = _wait_completed(client_arc7, sid)
    cfg = body.get("config_snapshot") or {}
    assert cfg.get("model_profile_id") == LOCAL_LMSTUDIO_DEFAULT_ID
    assert cfg.get("llm_provider") == "lmstudio"
    assert cfg.get("routing_policy") == "local_only"
    _assert_export_provenance(client_arc7, sid)


def test_post_run_hybrid_legacy_provider_provenance(client_arc7: TestClient) -> None:
    r = client_arc7.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 2,
            "random_seed": 9,
            "llm_provider": "hybrid",
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    body = _wait_completed(client_arc7, sid)
    turns = body.get("transcript") or []
    assert len(turns) == 2
    assert turns[0]["effective_provider"] == "anthropic"
    assert turns[0]["effective_profile_id"] == ANTHROPIC_DEFAULT_ID
    assert turns[1]["effective_provider"] == "lmstudio"
    assert turns[1]["effective_profile_id"] == LOCAL_LMSTUDIO_DEFAULT_ID
    cfg = body.get("config_snapshot") or {}
    assert cfg.get("routing_policy") == "hybrid_first_turn"
    _assert_export_provenance(client_arc7, sid)


def test_post_run_anthropic_profile_id(client_arc7: TestClient) -> None:
    r = client_arc7.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 10,
            "model_profile_id": ANTHROPIC_DEFAULT_ID,
            "llm_provider": "anthropic",
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    body = _wait_completed(client_arc7, sid)
    turns = body.get("transcript") or []
    assert turns[0]["effective_provider"] == "anthropic"
    assert turns[0]["effective_profile_id"] == ANTHROPIC_DEFAULT_ID
    _assert_export_provenance(client_arc7, sid)


def test_capabilities_model_profiles_after_arc7() -> None:
    from mirofish_backend.api.capabilities import build_capabilities_dict

    cap = build_capabilities_dict()
    mp = cap.get("model_profiles") or {}
    assert len(mp.get("profiles") or []) >= 2
    assert (mp.get("hybrid_routing") or {}).get("routing_policy") == "hybrid_first_turn"
