import json
import os
import tempfile

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_status_with_transcript
from mirofish_backend.db.schema import init_db
from mirofish_backend.simulation import orchestrator


async def _run_with_fake_llm(db_path: str, *, total_rounds: int = 2, seed: int = 42) -> dict:
    async def fake_llm_complete(**kwargs) -> str:
        system = kwargs["messages"][0]["content"]
        if "acting as a principal" in system:
            state = {
                "support_level": 0.72,
                "resistance_level": 0.28,
                "workload_stress": 0.41,
                "belief_posture": "supportive",
                "perceived_conflict": False,
            }
        elif "acting as a middle_manager" in system:
            state = {
                "support_level": 0.55,
                "resistance_level": 0.42,
                "workload_stress": 0.55,
                "belief_posture": "mixed",
                "perceived_conflict": True,
            }
        else:
            state = {
                "support_level": 0.51,
                "resistance_level": 0.44,
                "workload_stress": 0.59,
                "belief_posture": "classroom_caution",
                "perceived_conflict": False,
            }
        return "Policy-relevant stub reply.\n\n<state>\n" + json.dumps(state) + "\n</state>"

    original = orchestrator.llm_complete
    orchestrator.llm_complete = fake_llm_complete
    try:
        sim_id = await create_simulation_run(
            db_path,
            name="State Test",
            scenario_id="psle_reform_mvp",
            status="pending",
            total_rounds=total_rounds,
            random_seed=seed,
            prompt_version="v0",
            model_used="fake-model",
        )
        await orchestrator.run_simulation_task(
            sqlite_path=db_path,
            simulation_id=sim_id,
            scenario_id="psle_reform_mvp",
            total_rounds=total_rounds,
            agent_limit=3,
            random_seed=seed,
            prompt_version="v0",
            model_used="fake-model",
            lmstudio_model="fake-model",
            lmstudio_base_url="http://unused",
            llm_temperature=0.0,
            llm_max_tokens=512,
            working_memory_last_k=2,
            llm_provider="lmstudio",
            anthropic_api_key="",
            anthropic_model="unused",
            peer_context_max_chars=1200,
            rag_effective=False,
            embedding_model="unused-emb",
            rag_top_k=4,
            rag_chunk_size=400,
            rag_chunk_overlap=80,
            rag_max_inject_chars=2400,
        )
        res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
        assert res is not None
        return res
    finally:
        orchestrator.llm_complete = original


@pytest.mark.asyncio
async def test_state_timeline_and_demographics_are_persisted() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "state.sqlite")
        await init_db(db_path)

        res = await _run_with_fake_llm(db_path, total_rounds=2, seed=42)
        assert res["status"] == "completed"
        assert len(res["state_timeline"]) == 2
        assert len(res["outcome_indicators"]) == 2

        first_round = res["state_timeline"][0]
        assert len(first_round["agents"]) == 3
        first_agent = first_round["agents"][0]
        assert "demographics" in first_agent
        assert {"age", "sex", "ethnicity", "ses"} <= set(first_agent["demographics"].keys())
        assert all(a.get("spoke_this_round") is True for a in first_round["agents"])


@pytest.mark.asyncio
async def test_state_outcomes_are_deterministic_with_fixed_seed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "determinism.sqlite")
        await init_db(db_path)

        run1 = await _run_with_fake_llm(db_path, total_rounds=2, seed=7)
        run2 = await _run_with_fake_llm(db_path, total_rounds=2, seed=7)

        assert run1["outcome_indicators"] == run2["outcome_indicators"]
        assert run1["state_timeline"] == run2["state_timeline"]
