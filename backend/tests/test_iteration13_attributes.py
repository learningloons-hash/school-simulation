"""Iteration 13 — structured persona sections (YAML + population JSON) and state timeline."""

import csv
import io
import json
import os
import tempfile

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_status_with_transcript
from mirofish_backend.db.schema import init_db
from mirofish_backend.population.csv_population import (
    build_personas_and_slot_overrides,
    parse_population_csv,
    select_population_draw,
)
from mirofish_backend.scenarios.registry import get_scenario
from mirofish_backend.simulation import orchestrator


def test_psle_yaml_principal_loads_attribute_sections() -> None:
    cfg = get_scenario("psle_reform_mvp")
    p0 = cfg.personas[0]
    assert p0.identity.get("nationality") == "Singaporean"
    assert "policy_stance" in p0.attitudes
    assert p0.personal_history.get("years_in_role") == 8


def test_population_identity_json_parses_and_merges_into_overrides() -> None:
    scenario = get_scenario("psle_reform_mvp")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "persona_id",
            "sampling_weight",
            "stratum",
            "identity_json",
            "attitudes_json",
            "personal_history_json",
        ]
    )
    w.writerow(
        [
            "principal_001",
            "1.0",
            "A",
            json.dumps({"locale": "north"}),
            json.dumps({"stance": "pro"}),
            json.dumps({}),
        ]
    )
    text = buf.getvalue()
    res = parse_population_csv(text, scenario=scenario)
    idxs, _ = select_population_draw(res.rows, agent_limit=1, mode="weighted", random_seed=1)
    _personas, demos = build_personas_and_slot_overrides(scenario, res.rows, idxs)
    assert demos[0]["identity"]["locale"] == "north"
    assert demos[0]["attitudes"]["stance"] == "pro"


def test_population_invalid_identity_json_errors() -> None:
    scenario = get_scenario("psle_reform_mvp")
    text = "persona_id,sampling_weight,stratum,identity_json\nprincipal_001,1.0,A,not-json\n"
    with pytest.raises(ValueError, match="invalid JSON"):
        parse_population_csv(text, scenario=scenario)


def test_population_identity_json_must_be_object_not_array() -> None:
    scenario = get_scenario("psle_reform_mvp")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["persona_id", "sampling_weight", "stratum", "identity_json"])
    w.writerow(["principal_001", "1.0", "A", "[1,2,3]"])
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_population_csv(buf.getvalue(), scenario=scenario)


@pytest.mark.asyncio
async def test_state_timeline_includes_attribute_sections_after_run() -> None:
    async def fake_llm_complete(**kwargs) -> str:
        system = kwargs["messages"][0]["content"]
        assert "Identity (structured attributes)" in system
        assert "Singaporean" in system
        state = {
            "support_level": 0.6,
            "resistance_level": 0.3,
            "workload_stress": 0.4,
            "belief_posture": "supportive",
            "perceived_conflict": False,
        }
        return "Reply.\n\n<state>\n" + json.dumps(state) + "\n</state>"

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "attr13.sqlite")
        await init_db(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = fake_llm_complete
        try:
            sim_id = await create_simulation_run(
                db_path,
                name="Attr13",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=1,
                random_seed=1,
                prompt_version="v1",
                model_used="fake",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=1,
                agent_limit=3,
                random_seed=1,
                prompt_version="v1",
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
                rag_top_k=2,
                rag_chunk_size=200,
                rag_chunk_overlap=40,
                rag_max_inject_chars=800,
            )
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            r1 = res["state_timeline"][0]
            principal = next(a for a in r1["agents"] if a["agent_role"] == "principal")
            assert principal.get("attribute_sections", {}).get("identity", {}).get("nationality") == "Singaporean"
        finally:
            orchestrator.llm_complete = orig
