"""Senna Arc 8 iter-39 — structured-output provenance and model-ecosystem integration."""

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
from mirofish_backend.llm.model_profiles import (
    ANTHROPIC_DEFAULT_ID,
    LOCAL_LMSTUDIO_DEFAULT_ID,
    OPENAI_DEFAULT_ID,
)
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.llm.routing_policies import HEURISTIC_PROFILE_SENTINEL
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


def _state_json(support: float = 0.52) -> str:
    return json.dumps(
        {
            "support_level": support,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
    )


def _discard_create_task(coro: object, *_args: object, **_kwargs: object) -> None:
    if asyncio.iscoroutine(coro):
        coro.close()


async def _fake_llm_clean(**_kwargs: object) -> LLMCompletion:
    return LLMCompletion(
        text="OK.\n\n<state>\n" + _state_json() + "\n</state>",
        input_tokens=50,
        output_tokens=10,
    )


async def _fake_llm_no_state(**_kwargs: object) -> LLMCompletion:
    return LLMCompletion(
        text="We fully support this policy and will implement it.",
        input_tokens=40,
        output_tokens=8,
    )


async def _fake_llm_duplicate_state(**_kwargs: object) -> LLMCompletion:
    return LLMCompletion(
        text=(
            '<state>{"support_level": 0.1}</state>\n'
            "narrative\n"
            "<state>\n"
            + _state_json(0.88)
            + "\n</state>"
        ),
        input_tokens=55,
        output_tokens=12,
    )


def _wait_completed(client: TestClient, sim_id: str, *, max_poll: int = 200) -> dict[str, Any]:
    for _ in range(max_poll):
        body = client.get(f"/simulations/{sim_id}").json()
        if body.get("status") == "completed":
            return body
    raise AssertionError(f"simulation {sim_id} did not complete")


def _assert_state_provenance_export(client: TestClient, sim_id: str, *, expected_source: str) -> None:
    status = _wait_completed(client, sim_id)
    turns = status.get("transcript") or []
    assert turns
    assert turns[0].get("state_update_source") == expected_source

    ej = client.get(f"/simulations/{sim_id}/export.json")
    assert ej.status_code == 200
    ex_turns = ej.json().get("transcript") or []
    assert ex_turns[0].get("state_update_source") == expected_source

    zr = client.get(f"/simulations/{sim_id}/export.zip")
    assert zr.status_code == 200
    with zipfile.ZipFile(BytesIO(zr.content)) as zf:
        raw = zf.read("agent_turns.csv").decode("utf-8")
    rows = list(csv.reader(io.StringIO(raw)))
    assert "state_update_source" in rows[0]
    idx = rows[0].index("state_update_source")
    assert rows[1][idx] == expected_source


@pytest.fixture
def client_arc8(monkeypatch, tmp_path):
    db = tmp_path / "arc8.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))
    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", _fake_llm_clean)
    with TestClient(app) as c:
        yield c


def test_local_profile_state_update_source_model_parsed(client_arc8: TestClient) -> None:
    r = client_arc8.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 1,
            "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID,
        },
    )
    assert r.status_code == 200, r.text
    _assert_state_provenance_export(client_arc8, r.json()["id"], expected_source="model_parsed")


def test_anthropic_profile_path(client_arc8: TestClient) -> None:
    r = client_arc8.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 2,
            "model_profile_id": ANTHROPIC_DEFAULT_ID,
            "llm_provider": "anthropic",
        },
    )
    assert r.status_code == 200, r.text
    body = _wait_completed(client_arc8, r.json()["id"])
    t0 = (body.get("transcript") or [])[0]
    assert t0["effective_provider"] == "anthropic"
    assert t0["effective_profile_id"] == ANTHROPIC_DEFAULT_ID
    assert t0["state_update_source"] == "model_parsed"


def test_openai_compatible_profile_mock_path(monkeypatch, tmp_path) -> None:
    db = tmp_path / "arc8-openai.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    asyncio.run(init_db(str(db)))
    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", _fake_llm_clean)

    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 1,
                "agent_limit": 1,
                "random_seed": 3,
                "model_profile_id": OPENAI_DEFAULT_ID,
            },
        )
        assert r.status_code == 200, r.text
        body = _wait_completed(client, r.json()["id"])
        t0 = (body.get("transcript") or [])[0]
        assert t0["effective_profile_id"] == OPENAI_DEFAULT_ID
        assert t0["state_update_source"] == "model_parsed"
        cfg = body.get("config_snapshot") or {}
        assert cfg.get("model_profile_id") == OPENAI_DEFAULT_ID


def test_hybrid_routing_and_provenance(client_arc8: TestClient) -> None:
    r = client_arc8.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 2,
            "random_seed": 4,
            "llm_provider": "hybrid",
        },
    )
    assert r.status_code == 200, r.text
    body = _wait_completed(client_arc8, r.json()["id"])
    turns = body.get("transcript") or []
    assert len(turns) == 2
    assert turns[0]["effective_provider"] == "anthropic"
    assert turns[0]["state_update_source"] == "model_parsed"
    assert turns[1]["effective_provider"] == "lmstudio"
    assert turns[1]["state_update_source"] == "model_parsed"


def test_keyword_fallback_provenance(monkeypatch, tmp_path) -> None:
    db = tmp_path / "arc8-kw.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))
    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", _fake_llm_no_state)

    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 1,
                "agent_limit": 1,
                "random_seed": 5,
            },
        )
        assert r.status_code == 200, r.text
        _assert_state_provenance_export(client, r.json()["id"], expected_source="keyword_fallback")


def test_repaired_duplicate_state_provenance(monkeypatch, tmp_path) -> None:
    db = tmp_path / "arc8-repair.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))
    monkeypatch.setattr(
        "mirofish_backend.simulation.orchestrator.llm_complete",
        _fake_llm_duplicate_state,
    )

    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 1,
                "agent_limit": 1,
                "random_seed": 6,
            },
        )
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        body = _wait_completed(client, sid)
        assert (body.get("transcript") or [])[0]["state_update_source"] == "repaired"
        _assert_state_provenance_export(client, sid, expected_source="repaired")


def test_tier3_heuristic_profile_provenance(client_arc8: TestClient) -> None:
    roster = "slot,persona_id,fidelity_tier\n1,principal_001,3\n"
    r = client_arc8.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 7,
            "roster_csv": roster,
        },
    )
    assert r.status_code == 200, r.text
    body = _wait_completed(client_arc8, r.json()["id"])
    t0 = (body.get("transcript") or [])[0]
    assert t0["effective_provider"] == "heuristic"
    assert t0["effective_profile_id"] == HEURISTIC_PROFILE_SENTINEL
    assert t0.get("state_update_source") is None


@pytest.mark.asyncio
async def test_preflight_warnings_on_queue(tmp_path) -> None:
    from mirofish_backend.api import simulations as sim_api
    from mirofish_backend.api.simulations import SimulationRunRequest, queue_simulation_run

    settings = Settings(sqlite_path=str(tmp_path / "pf.sqlite"), llm_provider="hybrid")
    captured: dict[str, object] = {}

    async def fake_create(*_a, config_snapshot=None, **_kwargs):
        captured["config_snapshot"] = config_snapshot
        return "sim-arc8-pf"

    async def noop_guarded(**_kwargs):
        return None

    with (
        patch.object(sim_api, "create_simulation_run", side_effect=fake_create),
        patch.object(sim_api, "run_simulation_task_guarded", side_effect=noop_guarded),
        patch.object(sim_api, "load_scenario_for_run", return_value=(_minimal_scenario(), "builtin")),
        patch.object(sim_api.asyncio, "create_task", side_effect=_discard_create_task),
    ):
        resp = await queue_simulation_run(
            settings,
            SimulationRunRequest(
                scenario_id="psle_reform_mvp",
                total_rounds=2,
                agent_limit=2,
                llm_provider="hybrid",
            ),
        )

    snap = captured.get("config_snapshot")
    assert isinstance(snap, dict)
    assert isinstance(snap.get("preflight"), dict)
    assert any("preflight:" in w for w in resp.warnings)


def test_export_version_unchanged_with_state_source(client_arc8: TestClient) -> None:
    r = client_arc8.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 1,
            "random_seed": 8,
        },
    )
    assert r.status_code == 200
    ej = client_arc8.get(f"/simulations/{r.json()['id']}/export.json")
    assert ej.json().get("export_version") == EXPORT_VERSION


@pytest.mark.manual
def test_lmstudio_live_profile_smoke_skipped_in_ci() -> None:
    pytest.skip(
        "Live LM Studio: run `uv run python scripts/lmstudio_profile_smoke.py` "
        "with LM Studio on http://127.0.0.1:1234/v1"
    )
