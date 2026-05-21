"""Iteration 12: effective_provider persistence, run warnings, light stress timing (fake LLM)."""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.repo import create_simulation_run, get_simulation_export_bundle, get_simulation_status_with_transcript
from mirofish_backend.db.schema import init_db
from mirofish_backend.main import app
from mirofish_backend.simulation import orchestrator


@pytest.fixture
def client_skip_sim(monkeypatch, tmp_path):
    db = tmp_path / "iter12_api.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def skip_run(**kwargs):
        return None

    monkeypatch.setattr(
        "mirofish_backend.api.simulations.run_simulation_task_guarded",
        skip_run,
    )
    with TestClient(app) as c:
        yield c


def test_post_run_returns_warnings_for_unknown_roster_groups(client_skip_sim: TestClient) -> None:
    csv_text = "slot,persona_id,groups\n1,principal_001,made_up_faction\n"
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "fsbb_comparator",
            "agent_limit": 3,
            "total_rounds": 1,
            "roster_csv": csv_text,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("id")
    warns = body.get("warnings") or []
    assert warns
    assert "made_up_faction" in warns[0]


def test_post_run_returns_warnings_for_unknown_population_groups(client_skip_sim: TestClient) -> None:
    """Mirror roster path: population CSV groups must exist on scenario.groups."""
    pop_csv = (
        "persona_id,sampling_weight,stratum,groups\n"
        "principal_001,1.0,pool_a,made_up_pop_group\n"
        "middle_manager_001,1.0,pool_a,leadership\n"
        "teacher_001,1.0,pool_a,teaching_staff\n"
    )
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "fsbb_comparator",
            "agent_limit": 3,
            "total_rounds": 1,
            "population_csv": pop_csv,
            "population_sample_mode": "weighted",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("id")
    warns = body.get("warnings") or []
    assert warns
    assert any("made_up_pop_group" in w for w in warns)
    assert any("population" in w.lower() for w in warns)


async def _fake_llm_minimal(**kwargs) -> str:
    state = {
        "support_level": 0.5,
        "resistance_level": 0.5,
        "workload_stress": 0.5,
        "belief_posture": "neutral",
        "perceived_conflict": False,
    }
    return "Stub.\n\n<state>\n" + json.dumps(state) + "\n</state>"


@pytest.mark.asyncio
async def test_effective_provider_and_model_persisted_for_hybrid() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "hybrid.sqlite")
        await init_db(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _fake_llm_minimal
        try:
            sim_id = await create_simulation_run(
                db_path,
                name="Hybrid trace",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=2,
                random_seed=11,
                prompt_version="v0",
                model_used="hybrid:lm|anth",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=2,
                agent_limit=3,
                random_seed=11,
                prompt_version="v0",
                model_used="hybrid:lm|anth",
                lmstudio_model="local-llm-id",
                lmstudio_base_url="http://unused",
                llm_temperature=0.0,
                llm_max_tokens=256,
                working_memory_last_k=2,
                llm_provider="hybrid",
                anthropic_api_key="dummy",
                anthropic_model="claude-sonnet-test",
                peer_context_max_chars=1200,
                rag_effective=False,
                embedding_model="unused",
                rag_top_k=4,
                rag_chunk_size=400,
                rag_chunk_overlap=80,
                rag_max_inject_chars=2400,
            )
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            assert res["status"] == "completed"
            turns = res["transcript"]
            assert len(turns) == 6
            assert turns[0]["effective_provider"] == "anthropic"
            assert turns[0]["effective_model"] == "claude-sonnet-test"
            assert turns[0]["effective_profile_id"] == "anthropic_default"
            assert turns[1]["effective_provider"] == "lmstudio"
            assert turns[1]["effective_model"] == "local-llm-id"
            assert turns[1]["effective_profile_id"] == "local_lmstudio_default"
            assert turns[3]["effective_provider"] == "anthropic"
            bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
            assert bundle is not None
            assert bundle["transcript"][0]["effective_provider"] == "anthropic"
            assert bundle["transcript"][0]["effective_model"] == "claude-sonnet-test"
        finally:
            orchestrator.llm_complete = orig


@pytest.mark.asyncio
async def test_stress_many_fake_llm_turns_completes_quickly() -> None:
    """Timing harness: no real LLM; catches accidental quadratic work in the orchestrator loop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "stress.sqlite")
        await init_db(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _fake_llm_minimal
        try:
            sim_id = await create_simulation_run(
                db_path,
                name="Stress",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=5,
                random_seed=99,
                prompt_version="v0",
                model_used="fake",
            )
            t0 = time.perf_counter()
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=5,
                agent_limit=8,
                random_seed=99,
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
            elapsed = time.perf_counter() - t0
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            assert res["status"] == "completed"
            assert len(res["transcript"]) == 40  # 8 * 5
            assert elapsed < 5.0, f"expected fake-LLM batch to finish quickly, took {elapsed:.1f}s"
        finally:
            orchestrator.llm_complete = orig
