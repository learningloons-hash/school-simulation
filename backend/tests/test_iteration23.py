"""Iteration 23 — tier-aware orchestrator (Tier-2 simplified prompt, Tier-3 no LLM, fidelity_tier on turns)."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_export_bundle, get_simulation_status_with_transcript
from mirofish_backend.db.schema import init_db
from mirofish_backend.llm import prompt_templates
from mirofish_backend.scenarios.registry import get_scenario
from mirofish_backend.simulation import orchestrator


def test_simplified_persona_prompt_omits_deep_blocks() -> None:
    full = prompt_templates.build_system_prompt(
        scenario_id="s",
        role="r",
        name="N",
        style_cues="sc",
        beliefs={"k": 1},
        demographics={"age": 40},
        state={"support_level": 0.5, "resistance_level": 0.4, "workload_stress": 0.5, "belief_posture": "x"},
        prompt_version="v1",
        psychological_profile={"a": 1},
        implementation_profile={"b": 2},
        group_affiliations=("G",),
        identity={"id": 1},
        attitudes={"at": 1},
        personal_history={"ph": 1},
    )
    simp = prompt_templates.simplified_persona_prompt(
        scenario_id="s",
        role="r",
        name="N",
        style_cues="sc",
        beliefs={"k": 1},
        state={"support_level": 0.5, "resistance_level": 0.4, "workload_stress": 0.5, "belief_posture": "x"},
        prompt_version="v1",
    )
    assert "Psychological profile" in full
    assert "Identity (structured" in full
    assert "Psychological profile" not in simp
    assert "Identity (structured" not in simp
    assert "Implementation profile" not in simp
    assert "Fidelity: Tier 2" in simp


def test_tier_one_uses_full_system_prompt() -> None:
    """Tier-1 orchestrator path uses full `build_system_prompt`, not simplified Tier-2 (Iteration 23 DoD)."""
    text = prompt_templates.build_system_prompt(
        scenario_id="psle_reform_mvp",
        role="principal",
        name="Principal",
        style_cues="Formal.",
        beliefs={"trust_in_moe_policy": 0.55},
        demographics={"age": 50, "sex": "female", "ethnicity": "unspecified", "ses": "unspecified"},
        state={
            "support_level": 0.62,
            "resistance_level": 0.30,
            "workload_stress": 0.40,
            "belief_posture": "strategic_support",
        },
        prompt_version="v1",
        psychological_profile={},
        implementation_profile={},
        group_affiliations=(),
        identity={},
        attitudes={},
        personal_history={},
    )
    assert "Persona identity and stance:" in text
    assert "Fidelity: Tier 2" not in text


@pytest.mark.asyncio
async def test_mixed_tiers_llm_only_for_one_and_two() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = cfg.personas[:3]
    llm_calls: list[dict[str, str]] = []

    async def fake_llm_complete(**kwargs) -> str:
        sys_c = kwargs["messages"][0]["content"]
        llm_calls.append({"system": sys_c})
        state = {
            "support_level": 0.6,
            "resistance_level": 0.35,
            "workload_stress": 0.45,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return "Stub.\n\n<state>\n" + json.dumps(state) + "\n</state>"

    orig = orchestrator.llm_complete
    orchestrator.llm_complete = fake_llm_complete
    try:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "iter23.sqlite")
            await init_db(db_path)
            sim_id = await create_simulation_run(
                db_path,
                name="TierMix",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=1,
                random_seed=99,
                prompt_version="v1",
                model_used="fake",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=1,
                agent_limit=3,
                random_seed=99,
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
                rag_top_k=4,
                rag_chunk_size=400,
                rag_chunk_overlap=80,
                rag_max_inject_chars=2400,
                personas_for_run=personas,
                scenario_config=cfg,
                fidelity_tiers=[1, 2, 3],
            )
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            assert res["status"] == "completed"
            tr = res["transcript"]
            assert len(tr) == 3
            assert [x["fidelity_tier"] for x in tr] == [1, 2, 3]
            assert tr[2]["raw_response"] == "[Tier 3 — heuristic state update]"
            assert tr[2]["effective_provider"] == "heuristic"
            assert tr[2]["effective_profile_id"] == "heuristic"
            assert tr[2]["latency_ms"] == 0
            assert len(llm_calls) == 2
            # Parallel gather: completion order ≠ turn order — classify prompts by content.
            tier1_full = [
                c
                for c in llm_calls
                if "Persona identity and stance:" in c["system"] and "Fidelity: Tier 2" not in c["system"]
            ]
            tier2_simp = [c for c in llm_calls if "Fidelity: Tier 2" in c["system"]]
            assert len(tier1_full) == 1
            assert len(tier2_simp) == 1

            bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
            assert bundle is not None
            bt = bundle["transcript"]
            assert bt[2]["fidelity_tier"] == 3
    finally:
        orchestrator.llm_complete = orig


@pytest.mark.asyncio
async def test_tier_three_preserves_prior_state_across_rounds() -> None:
    """Tier-3 agent state should not move when only Tier-3 'speaks' (placeholder)."""
    cfg = get_scenario("psle_reform_mvp")
    personas = [cfg.personas[2]]  # teacher only
    teacher_initial = orchestrator._initial_state_from_persona(personas[0])

    async def fake_llm_complete(**_kwargs) -> str:
        raise AssertionError("LLM should not be called for Tier-3-only run")

    orig = orchestrator.llm_complete
    orchestrator.llm_complete = fake_llm_complete
    try:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "iter23_t3.sqlite")
            await init_db(db_path)
            sim_id = await create_simulation_run(
                db_path,
                name="T3Only",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=2,
                random_seed=1,
                prompt_version="v1",
                model_used="fake",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=2,
                agent_limit=1,
                random_seed=1,
                prompt_version="v1",
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
                rag_top_k=4,
                rag_chunk_size=400,
                rag_chunk_overlap=80,
                rag_max_inject_chars=2400,
                personas_for_run=personas,
                scenario_config=cfg,
                fidelity_tiers=[3],
            )
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            timeline = res.get("state_timeline") or []
            for entry in timeline:
                for ag in entry.get("agents") or []:
                    if ag["agent_id"].startswith("teacher_001"):
                        assert ag["support_level"] == pytest.approx(teacher_initial.support_level)
                        assert ag["resistance_level"] == pytest.approx(teacher_initial.resistance_level)
                        assert ag["workload_stress"] == pytest.approx(teacher_initial.workload_stress)
    finally:
        orchestrator.llm_complete = orig
