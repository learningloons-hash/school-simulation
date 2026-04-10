import json
import os
import tempfile

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_status_with_transcript
from mirofish_backend.db.schema import init_db
from mirofish_backend.roster.csv_roster import personas_for_run
from mirofish_backend.scenarios.registry import get_scenario
from mirofish_backend.api.simulations import speakers_per_round_for_config_snapshot
from mirofish_backend.simulation import orchestrator
from mirofish_backend.simulation.orchestrator import _agents_for_round, _build_agent_instances


def test_speakers_per_round_config_snapshot_full_robin_null() -> None:
    assert speakers_per_round_for_config_snapshot("full_round_robin", 2) is None
    assert speakers_per_round_for_config_snapshot("sample_k_per_round", 3) == 3


def test_agents_for_round_full_roster() -> None:
    scenario = get_scenario("psle_reform_mvp")
    personas = scenario.personas[:3]
    agents = _build_agent_instances(scenario, personas)
    got = _agents_for_round(agents, round_number=1, simulation_mode="full_round_robin", speakers_per_round=2, random_seed=1)
    assert [a.agent_id for a in got] == [a.agent_id for a in agents]


def test_agents_for_round_sample_k_deterministic() -> None:
    scenario = get_scenario("psle_reform_mvp")
    # five slots using repeated personas
    personas = personas_for_run(scenario, 5, None)
    agents = _build_agent_instances(scenario, personas)
    a = _agents_for_round(agents, round_number=1, simulation_mode="sample_k_per_round", speakers_per_round=2, random_seed=99)
    b = _agents_for_round(agents, round_number=1, simulation_mode="sample_k_per_round", speakers_per_round=2, random_seed=99)
    assert [x.agent_id for x in a] == [x.agent_id for x in b]
    assert len(a) == 2
    c = _agents_for_round(agents, round_number=2, simulation_mode="sample_k_per_round", speakers_per_round=2, random_seed=99)
    assert len(c) == 2
    # Different round → usually different subset (not asserting inequality, just length)


@pytest.mark.asyncio
async def test_sample_k_fewer_llm_turns_than_full_robin() -> None:
    async def fake_llm_complete(**kwargs) -> str:
        state = {
            "support_level": 0.5,
            "resistance_level": 0.4,
            "workload_stress": 0.5,
            "belief_posture": "mixed",
            "perceived_conflict": False,
        }
        return "Stub.\n\n<state>\n" + json.dumps(state) + "\n</state>"

    original = orchestrator.llm_complete
    orchestrator.llm_complete = fake_llm_complete
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "s.sqlite")
            await init_db(db_path)
            sim_id = await create_simulation_run(
                db_path,
                name="SampleK",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=1,
                random_seed=42,
                prompt_version="v0",
                model_used="fake",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=1,
                agent_limit=5,
                random_seed=42,
                prompt_version="v0",
                model_used="fake",
                lmstudio_model="fake",
                lmstudio_base_url="http://unused",
                llm_temperature=0.0,
                llm_max_tokens=256,
                working_memory_last_k=2,
                llm_provider="lmstudio",
                anthropic_api_key="",
                anthropic_model="unused",
                peer_context_max_chars=1200,
                rag_effective=False,
                embedding_model="unused",
                rag_top_k=4,
                rag_chunk_size=400,
                rag_chunk_overlap=80,
                rag_max_inject_chars=2400,
                simulation_mode="sample_k_per_round",
                speakers_per_round=2,
            )
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            assert res["status"] == "completed"
            assert len(res["transcript"]) == 2
            tl = res["state_timeline"]
            assert len(tl) == 1
            agents = tl[0]["agents"]
            assert len(agents) == 5
            assert sum(1 for a in agents if a.get("spoke_this_round") is True) == 2
            assert sum(1 for a in agents if a.get("spoke_this_round") is False) == 3
    finally:
        orchestrator.llm_complete = original
