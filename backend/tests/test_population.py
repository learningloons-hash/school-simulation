"""Iteration 11 — population pool CSV parse, draw determinism, persona merge."""

import json
import os
import tempfile

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_status_with_transcript
from mirofish_backend.db.schema import init_db
from mirofish_backend.population import csv_population
from mirofish_backend.population.csv_population import (
    build_personas_and_demographic_overrides,
    parse_population_csv,
    select_population_draw,
)
from mirofish_backend.roster.csv_roster import merge_persona_for_slot, parse_roster_csv
from mirofish_backend.scenarios.registry import get_scenario
from mirofish_backend.simulation import orchestrator


def _pool_psle(n: int) -> str:
    lines = ["persona_id,sampling_weight,stratum,age,sex,ethnicity,ses,name,groups"]
    for i in range(n):
        lines.append(f"principal_001,1.0,A,{40 + i},female,Chinese,high,P{i},")
    return "\n".join(lines) + "\n"


def test_parse_population_csv_unknown_persona() -> None:
    scenario = get_scenario("psle_reform_mvp")
    csv = "persona_id\nghost\n"
    with pytest.raises(ValueError, match="unknown persona_id"):
        parse_population_csv(csv, scenario=scenario)


def test_weighted_draw_is_deterministic() -> None:
    scenario = get_scenario("psle_reform_mvp")
    text = _pool_psle(5)
    res = parse_population_csv(text, scenario=scenario)
    a, _ = select_population_draw(res.rows, agent_limit=3, mode="weighted", random_seed=999)
    b, _ = select_population_draw(res.rows, agent_limit=3, mode="weighted", random_seed=999)
    c, _ = select_population_draw(res.rows, agent_limit=3, mode="weighted", random_seed=1000)
    assert a == b
    assert a != c


def test_stratified_draw_respects_quota() -> None:
    scenario = get_scenario("psle_reform_mvp")
    lines = ["persona_id,sampling_weight,stratum,age,sex,ethnicity,ses,name,groups"]
    for i in range(4):
        lines.append(f"principal_001,1.0,X,{30 + i},female,Chinese,high,X{i},")
    for i in range(4):
        lines.append(f"principal_001,1.0,Y,{40 + i},male,Malay,middle,Y{i},")
    text = "\n".join(lines) + "\n"
    res = parse_population_csv(text, scenario=scenario)
    idxs, trace = select_population_draw(res.rows, agent_limit=4, mode="stratified", random_seed=42)
    assert len(idxs) == 4
    assert len(trace) == 4
    by_stratum: dict[str, int] = {}
    for t in trace:
        by_stratum[t.stratum] = by_stratum.get(t.stratum, 0) + 1
    assert by_stratum.get("X", 0) >= 1
    assert by_stratum.get("Y", 0) >= 1


def test_pool_smaller_than_agent_limit_errors() -> None:
    scenario = get_scenario("psle_reform_mvp")
    res = parse_population_csv(_pool_psle(2), scenario=scenario)
    with pytest.raises(ValueError, match="pool has"):
        select_population_draw(res.rows, agent_limit=5, mode="weighted", random_seed=1)


def test_stratified_raises_when_stratum_quota_exceeds_row_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guards oversubscription if quota logic ever diverges from stratum sizes (architect review)."""
    scenario = get_scenario("psle_reform_mvp")
    lines = [
        "persona_id,sampling_weight,stratum,age,sex,ethnicity,ses,name,groups",
        "principal_001,1.0,X,40,female,Chinese,high,AX,",
        "principal_001,1.0,Y,41,male,Malay,middle,BY1,",
        "principal_001,1.0,Y,42,male,Malay,middle,BY2,",
    ]
    text = "\n".join(lines) + "\n"
    res = parse_population_csv(text, scenario=scenario)

    def _bad_quota(_sizes: dict[str, int], k: int) -> dict[str, int]:
        return {"X": 2, "Y": 1}

    monkeypatch.setattr(csv_population, "_quota_per_stratum", _bad_quota)
    with pytest.raises(ValueError, match="needs 2 draws but only has 1 rows"):
        select_population_draw(res.rows, agent_limit=3, mode="stratified", random_seed=1)


def test_demographic_overrides_merge() -> None:
    scenario = get_scenario("psle_reform_mvp")
    text = _pool_psle(3)
    res = parse_population_csv(text, scenario=scenario)
    idxs, _ = select_population_draw(res.rows, agent_limit=3, mode="weighted", random_seed=7)
    personas, demos = build_personas_and_demographic_overrides(scenario, res.rows, idxs)
    assert len(personas) == 3
    assert demos[0]["age"] == 40 + idxs[0]


@pytest.mark.asyncio
async def test_population_run_persists_demographics_in_timeline() -> None:
    async def fake_llm_complete(**kwargs) -> str:
        state = {
            "support_level": 0.5,
            "resistance_level": 0.4,
            "workload_stress": 0.5,
            "belief_posture": "mixed",
            "perceived_conflict": False,
        }
        return "OK.\n\n<state>\n" + json.dumps(state) + "\n</state>"

    original = orchestrator.llm_complete
    orchestrator.llm_complete = fake_llm_complete
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "p.sqlite")
            await init_db(db_path)
            scenario = get_scenario("psle_reform_mvp")
            pop = parse_population_csv(_pool_psle(4), scenario=scenario)
            idxs, _ = select_population_draw(pop.rows, agent_limit=2, mode="weighted", random_seed=123)
            personas, demos = build_personas_and_demographic_overrides(scenario, pop.rows, idxs)
            sim_id = await create_simulation_run(
                db_path,
                name="Pop",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=1,
                random_seed=123,
                prompt_version="v0",
                model_used="fake",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=1,
                agent_limit=2,
                random_seed=123,
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
                personas_for_run=personas,
                slot_overrides=demos,
            )
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            agents = res["state_timeline"][0]["agents"]
            ages = {a["demographics"]["age"] for a in agents}
            expected_ages = {40 + idxs[0], 40 + idxs[1]}
            assert ages == expected_ages
    finally:
        orchestrator.llm_complete = original


def test_roster_overlays_population_persona() -> None:
    scenario = get_scenario("psle_reform_mvp")
    pop = parse_population_csv(_pool_psle(3), scenario=scenario)
    idxs, _ = select_population_draw(pop.rows, agent_limit=2, mode="weighted", random_seed=5)
    personas, _ = build_personas_and_demographic_overrides(scenario, pop.rows, idxs)
    roster = parse_roster_csv(
        "slot,persona_id,name\n1,,Overlay Name\n",
        agent_limit=2,
        scenario=scenario,
    )
    merged = [
        merge_persona_for_slot(personas[i], roster.by_slot.get(i + 1)) for i in range(len(personas))
    ]
    assert merged[0].name == "Overlay Name"
    assert merged[1].name == "P" + str(idxs[1])
