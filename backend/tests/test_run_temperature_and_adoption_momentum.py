"""Per-run llm_temperature override and adoption_momentum round-1 null."""

from __future__ import annotations

import asyncio
import json
import os

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.schema import init_db
from mirofish_backend.main import app
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.simulation import orchestrator


def _fake_state_json() -> str:
    state = {
        "support_level": 0.55,
        "resistance_level": 0.45,
        "workload_stress": 0.50,
        "belief_posture": "neutral",
        "perceived_conflict": False,
    }
    return "OK.\n\n<state>\n" + json.dumps(state) + "\n</state>"


async def _fake_llm_instant(**kwargs) -> LLMCompletion:
    return LLMCompletion(text=_fake_state_json(), input_tokens=8, output_tokens=8)


@pytest.fixture
def client_skip_sim(monkeypatch, tmp_path):
    db = tmp_path / "temp_adoption.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))

    async def _noop_task(**_kwargs):
        return None

    monkeypatch.setattr("mirofish_backend.api.simulations.run_simulation_task_guarded", _noop_task)
    with TestClient(app) as c:
        yield c, db


def _wait_completed(client: TestClient, sim_id: str) -> dict:
    import time

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        r = client.get(f"/simulations/{sim_id}")
        if r.status_code == 200:
            body = r.json()
            if body.get("status") in ("completed", "failed"):
                return body
        time.sleep(0.05)
    raise AssertionError(f"simulation {sim_id} did not complete")


def test_llm_temperature_defaults_to_settings(client_skip_sim, monkeypatch) -> None:
    client, _db = client_skip_sim
    monkeypatch.setenv("LLM_TEMPERATURE", "0.25")

    r = client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 2,
            "agent_limit": 2,
            "random_seed": 1,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    body = client.get(f"/simulations/{sid}").json()
    assert (body.get("config_snapshot") or {}).get("llm_temperature") == 0.25


def test_llm_temperature_request_override(client_skip_sim, monkeypatch) -> None:
    client, _db = client_skip_sim
    monkeypatch.setenv("LLM_TEMPERATURE", "0.25")

    r = client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 2,
            "agent_limit": 2,
            "random_seed": 2,
            "llm_temperature": 0.8,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    body = client.get(f"/simulations/{sid}").json()
    assert (body.get("config_snapshot") or {}).get("llm_temperature") == 0.8


def test_adoption_momentum_null_on_round_one(monkeypatch, tmp_path) -> None:
    db = tmp_path / "adoption_r1.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))
    orchestrator.llm_complete = _fake_llm_instant

    async def _run() -> None:
        from mirofish_backend.db.repo import create_simulation_run

        sim_id = await create_simulation_run(
            str(db),
            name="adoption-test",
            scenario_id="psle_reform_mvp",
            status="pending",
            total_rounds=3,
            random_seed=3,
            prompt_version="v0",
            model_used="fake",
            config_snapshot={},
        )
        await orchestrator.run_simulation_task(
            sqlite_path=str(db),
            simulation_id=sim_id,
            scenario_id="psle_reform_mvp",
            total_rounds=3,
            agent_limit=2,
            random_seed=3,
            prompt_version="v0",
            model_used="fake",
            lmstudio_model="fake",
            lmstudio_base_url="http://unused",
            llm_temperature=0.0,
            llm_max_tokens=128,
            working_memory_last_k=2,
            llm_provider="lmstudio",
            anthropic_api_key="",
            anthropic_model="unused",
            peer_context_max_chars=800,
            rag_effective=False,
            embedding_model="unused",
            rag_top_k=2,
            rag_chunk_size=200,
            rag_chunk_overlap=40,
            rag_max_inject_chars=800,
        )
        from mirofish_backend.db.repo import get_simulation_export_bundle

        bundle = await get_simulation_export_bundle(str(db), simulation_id=sim_id)
        assert bundle is not None
        outcomes = bundle.get("round_outcomes") or []
        assert len(outcomes) == 3
        assert outcomes[0].get("adoption_momentum") is None
        assert isinstance(outcomes[1].get("adoption_momentum"), float)
        assert isinstance(outcomes[2].get("adoption_momentum"), float)
        indicators = bundle.get("outcome_indicators") or []
        assert indicators[0].get("adoption_momentum") is None
        assert isinstance(indicators[1].get("adoption_momentum"), float)

    asyncio.run(_run())
