"""Iteration 24 — Tier-3 heuristic, hybrid_core_remainder, synthetic remainders, agent_limit 300."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_status_with_transcript
from mirofish_backend.db.schema import init_db
from mirofish_backend.scenarios.registry import get_scenario
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.simulation import orchestrator
from mirofish_backend.simulation.remainder import build_synthetic_remainder_personas, is_synthetic_remainder_persona
from mirofish_backend.simulation.sampling_strategy import compute_fidelity_tiers


def test_hybrid_core_remainder_synthetic_always_tier3() -> None:
    cfg = get_scenario("psle_reform_mvp")
    core = [cfg.personas[0], cfg.personas[1]]
    synth = build_synthetic_remainder_personas(cfg, 2, random_seed=7)
    personas = core + synth
    tiers, rats = compute_fidelity_tiers(
        sampling_strategy="hybrid_core_remainder",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert tiers == [1, 2, 3, 3]
    assert all("synthetic remainder" in rats[i].lower() for i in (2, 3))
    assert is_synthetic_remainder_persona(synth[0])


@pytest.mark.asyncio
async def test_tier3_heuristic_tracks_tier1_delta() -> None:
    """One Tier-1 + one Tier-3 in round: LLM bumps Tier-1 support; Tier-3 follows dampened mean delta."""
    import tempfile

    cfg = get_scenario("psle_reform_mvp")
    synth_one = build_synthetic_remainder_personas(cfg, 1, random_seed=5)
    personas = [cfg.personas[0]] + synth_one  # Tier 1 + Tier 3
    tiers, _ = compute_fidelity_tiers(
        sampling_strategy="hybrid_core_remainder",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert tiers[0] == 1 and tiers[1] == 3

    async def fake_llm_complete(**_kwargs) -> LLMCompletion:
        state = {
            "support_level": 0.95,
            "resistance_level": 0.20,
            "workload_stress": 0.30,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return LLMCompletion(text="ok\n\n<state>\n" + json.dumps(state) + "\n</state>", input_tokens=6, output_tokens=6)

    orig = orchestrator.llm_complete
    orchestrator.llm_complete = fake_llm_complete
    try:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "i24.sqlite")
            await init_db(db_path)
            sim_id = await create_simulation_run(
                db_path,
                name="Heur",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=1,
                random_seed=11,
                prompt_version="v1",
                model_used="fake",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=1,
                agent_limit=2,
                random_seed=11,
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
                fidelity_tiers=tiers,
                tier_3_dampening=1.0,
                tier_3_noise_std=0.0,
            )
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            timeline = res.get("state_timeline") or []
            assert len(timeline) >= 1
            t3_snap = next(
                (
                    ag
                    for ag in timeline[-1].get("agents") or []
                    if ag["agent_id"].startswith("synthetic_remainder")
                ),
                None,
            )
            assert t3_snap is not None
            assert float(t3_snap["support_level"]) > 0.52
    finally:
        orchestrator.llm_complete = orig


@pytest.mark.asyncio
async def test_stress_30_tier1_and_270_tier3_under_15s() -> None:
    """Opus stress shape: 30 core (same role_level) + 270 synthetic, 2 rounds, fake LLM."""
    cfg = get_scenario("psle_reform_mvp")
    core = [cfg.personas[0]] * 30
    synth = build_synthetic_remainder_personas(cfg, 270, random_seed=99)
    personas = core + synth
    assert len(personas) == 300
    tiers, _ = compute_fidelity_tiers(
        sampling_strategy="hybrid_core_remainder",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert sum(1 for t in tiers if t == 1) == 30
    assert sum(1 for t in tiers if t == 3) == 270

    async def fake_llm_complete(**_kwargs) -> LLMCompletion:
        state: dict[str, Any] = {
            "support_level": 0.55,
            "resistance_level": 0.35,
            "workload_stress": 0.45,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return LLMCompletion(text="x\n\n<state>\n" + json.dumps(state) + "\n</state>", input_tokens=4, output_tokens=4)

    orig = orchestrator.llm_complete
    orchestrator.llm_complete = fake_llm_complete
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "i24_stress.sqlite")
            await init_db(db_path)
            sim_id = await create_simulation_run(
                db_path,
                name="Stress",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=2,
                random_seed=99,
                prompt_version="v1",
                model_used="fake",
            )
            t0 = time.perf_counter()
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=2,
                agent_limit=300,
                random_seed=99,
                prompt_version="v1",
                model_used="fake",
                lmstudio_model="fake",
                lmstudio_base_url="http://unused",
                llm_temperature=0.0,
                llm_max_tokens=64,
                working_memory_last_k=1,
                llm_provider="lmstudio",
                anthropic_api_key="",
                anthropic_model="unused",
                peer_context_max_chars=400,
                rag_effective=False,
                embedding_model="unused",
                rag_top_k=2,
                rag_chunk_size=200,
                rag_chunk_overlap=40,
                rag_max_inject_chars=800,
                personas_for_run=personas,
                scenario_config=cfg,
                fidelity_tiers=tiers,
                llm_concurrency_cap=16,
                tier_3_dampening=0.6,
                tier_3_noise_std=0.0,
            )
            elapsed = time.perf_counter() - t0
            assert elapsed < 15.0, f"stress wall time {elapsed:.2f}s exceeds 15s budget"
            res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
            assert res is not None
            assert res["status"] == "completed"
            assert len(res["transcript"]) == 300 * 2
    finally:
        orchestrator.llm_complete = orig
