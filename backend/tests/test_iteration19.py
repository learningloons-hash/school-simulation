"""Iteration 19: parallel LLM within rounds — concurrency cap, determinism, error isolation."""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.repo import (
    create_simulation_run,
    get_simulation_status_with_transcript,
)
from mirofish_backend.db.schema import init_db
from mirofish_backend.main import app
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.simulation import orchestrator


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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
    """Instant fake LLM — no I/O, returns a valid state block."""
    return LLMCompletion(text=_fake_state_json(), input_tokens=8, output_tokens=8)


_COMMON_KWARGS: dict = dict(
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


async def _run(db_path: str, sim_id: str, *, agents: int, rounds: int, seed: int, cap: int) -> None:
    await orchestrator.run_simulation_task(
        sqlite_path=db_path,
        simulation_id=sim_id,
        scenario_id="psle_reform_mvp",
        total_rounds=rounds,
        agent_limit=agents,
        random_seed=seed,
        llm_concurrency_cap=cap,
        **_COMMON_KWARGS,
    )


# ---------------------------------------------------------------------------
# 1. Parallel execution — all turns written
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parallel_execution_all_turns_written() -> None:
    """With cap=4 all turns must be written and the run must complete."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "par_all.sqlite")
        await init_db(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _fake_llm_instant
        try:
            sim_id = await create_simulation_run(
                db_path, name="par_all", scenario_id="psle_reform_mvp",
                status="pending", total_rounds=2, random_seed=7,
                prompt_version="v0", model_used="fake",
            )
            await _run(db_path, sim_id, agents=4, rounds=2, seed=7, cap=4)
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
        finally:
            orchestrator.llm_complete = orig

    assert res is not None
    assert res["status"] == "completed"
    assert len(res["transcript"]) == 8  # 4 agents × 2 rounds


# ---------------------------------------------------------------------------
# 2. Determinism — cap=1 (sequential) vs cap=4 produce identical turn order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sequential_and_parallel_produce_same_turn_order() -> None:
    """Turn assignment (turn_index, agent_id, interaction_type) must be identical
    regardless of concurrency cap when the same random_seed is used."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_seq = os.path.join(tmpdir, "det_seq.sqlite")
        db_par = os.path.join(tmpdir, "det_par.sqlite")
        await init_db(db_seq)
        await init_db(db_par)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _fake_llm_instant
        try:
            sid_seq = await create_simulation_run(
                db_seq, name="det_seq", scenario_id="psle_reform_mvp",
                status="pending", total_rounds=3, random_seed=42,
                prompt_version="v0", model_used="fake",
            )
            sid_par = await create_simulation_run(
                db_par, name="det_par", scenario_id="psle_reform_mvp",
                status="pending", total_rounds=3, random_seed=42,
                prompt_version="v0", model_used="fake",
            )
            await _run(db_seq, sid_seq, agents=3, rounds=3, seed=42, cap=1)
            await _run(db_par, sid_par, agents=3, rounds=3, seed=42, cap=4)

            res_seq = await get_simulation_status_with_transcript(db_seq, simulation_id=sid_seq)
            res_par = await get_simulation_status_with_transcript(db_par, simulation_id=sid_par)
        finally:
            orchestrator.llm_complete = orig

    assert res_seq is not None and res_par is not None
    turns_seq = res_seq["transcript"]
    turns_par = res_par["transcript"]
    assert len(turns_seq) == len(turns_par) == 9  # 3 × 3

    for t_s, t_p in zip(turns_seq, turns_par):
        assert t_s["round_number"] == t_p["round_number"], "round mismatch"
        assert t_s["turn_index"] == t_p["turn_index"], "turn_index mismatch"
        assert t_s["agent_id"] == t_p["agent_id"], "agent_id mismatch"
        assert t_s["interaction_type"] == t_p["interaction_type"], "interaction_type mismatch"


# ---------------------------------------------------------------------------
# 3. Error isolation — one LLM failure does not abort the round
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_error_isolation_one_llm_failure_does_not_abort_round() -> None:
    """If the LLM raises for one agent in a round the other agents still complete
    and the run reaches 'completed' status.  The failing turn is recorded with an
    [LLM error] prefix rather than silently dropped."""
    _calls: list[int] = []

    async def _llm_raises_on_second(**kwargs) -> LLMCompletion:
        _calls.append(1)
        n = len(_calls)
        if n == 2:
            raise RuntimeError("Simulated LLM crash on turn 2")
        return LLMCompletion(text=_fake_state_json(), input_tokens=8, output_tokens=8)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "err_iso.sqlite")
        await init_db(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _llm_raises_on_second
        try:
            sim_id = await create_simulation_run(
                db_path, name="err_iso", scenario_id="psle_reform_mvp",
                status="pending", total_rounds=1, random_seed=3,
                prompt_version="v0", model_used="fake",
            )
            await _run(db_path, sim_id, agents=3, rounds=1, seed=3, cap=3)
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
        finally:
            orchestrator.llm_complete = orig

    assert res is not None
    assert res["status"] == "completed", "run must still complete despite one LLM failure"
    turns = res["transcript"]
    assert len(turns) == 3, "all 3 turns must be written (error turns use error-string response)"

    # The failing turn's raw_response should contain the error marker
    error_turns = [t for t in turns if t.get("raw_response", "").startswith("[LLM error]")]
    assert len(error_turns) == 1


# ---------------------------------------------------------------------------
# 4. Stress test — 40 fake-LLM turns complete quickly under parallel cap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stress_40_turns_parallel_completes_quickly() -> None:
    """8 agents × 5 rounds = 40 turns with fake instant LLM must finish in < 5 s.
    Catches accidental O(N²) work or incorrect awaiting inside the gather loop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "stress19.sqlite")
        await init_db(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _fake_llm_instant
        try:
            sim_id = await create_simulation_run(
                db_path, name="stress19", scenario_id="psle_reform_mvp",
                status="pending", total_rounds=5, random_seed=99,
                prompt_version="v0", model_used="fake",
            )
            t0 = time.perf_counter()
            await _run(db_path, sim_id, agents=8, rounds=5, seed=99, cap=4)
            elapsed = time.perf_counter() - t0
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
        finally:
            orchestrator.llm_complete = orig

    assert res is not None
    assert res["status"] == "completed"
    assert len(res["transcript"]) == 40, "8 × 5 = 40 turns expected"
    assert elapsed < 5.0, f"expected parallel fake-LLM batch < 5 s, took {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# 5. API — llm_concurrency_cap stored in config_snapshot
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_skip_sim(monkeypatch, tmp_path):
    db = tmp_path / "iter19_api.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def skip_run(**kwargs) -> None:
        return None

    monkeypatch.setattr(
        "mirofish_backend.api.simulations.run_simulation_task_guarded",
        skip_run,
    )
    with TestClient(app) as c:
        yield c


def test_api_concurrency_cap_stored_in_config_snapshot(client_skip_sim: TestClient) -> None:
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "agent_limit": 2,
            "total_rounds": 1,
            "llm_concurrency_cap": 3,
        },
    )
    assert r.status_code == 200, r.text
    sim_id = r.json()["id"]

    r2 = client_skip_sim.get(f"/simulations/{sim_id}")
    assert r2.status_code == 200
    config = r2.json().get("config_snapshot") or {}
    assert config.get("llm_concurrency_cap") == 3


def test_api_default_concurrency_cap_in_config_snapshot(client_skip_sim: TestClient) -> None:
    """Omitting llm_concurrency_cap must store the server default (4)."""
    r = client_skip_sim.post(
        "/simulations/run",
        json={"scenario_id": "psle_reform_mvp", "agent_limit": 2, "total_rounds": 1},
    )
    assert r.status_code == 200, r.text
    sim_id = r.json()["id"]

    r2 = client_skip_sim.get(f"/simulations/{sim_id}")
    assert r2.status_code == 200
    config = r2.json().get("config_snapshot") or {}
    assert config.get("llm_concurrency_cap") == 4


def test_api_concurrency_cap_out_of_range_rejected(client_skip_sim: TestClient) -> None:
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "agent_limit": 2,
            "total_rounds": 1,
            "llm_concurrency_cap": 0,  # must be >= 1
        },
    )
    assert r.status_code == 422
