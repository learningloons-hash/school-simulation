"""scenario-context-field Part A — ScenarioConfig.context + prompt injection."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from mirofish_backend.db.repo import create_simulation_run
from mirofish_backend.db.schema import init_db
from mirofish_backend.llm.prompt_templates import (
    ORGANISATIONAL_CONTEXT_TITLE,
    build_system_prompt,
    simplified_persona_prompt,
)
from mirofish_backend.scenarios.registry import get_scenario, scenario_from_mapping
from mirofish_backend.scenarios.serialize import scenario_config_to_document
from mirofish_backend.simulation import orchestrator

SENTINEL = "SENNA_CTX_SENTINEL_7f3a9c"

_GOLDEN_TIER1_KWARGS = dict(
    scenario_id="psle_reform_mvp",
    role="principal",
    name="Principal",
    style_cues="Formal.",
    beliefs={"k": 1},
    demographics={"age": 40},
    state={
        "support_level": 0.5,
        "resistance_level": 0.3,
        "workload_stress": 0.4,
        "belief_posture": "strategic_support",
    },
    prompt_version="v1",
)

_GOLDEN_TIER1_PROMPT = (
    "You are Principal, acting as a principal in scenario 'psle_reform_mvp'.\n"
    "Prompt version: v1.\n\n"
    "Persona identity and stance:\n"
    "- Style cues: Formal.\n"
    "- Beliefs: {'k': 1}\n"
    "- Demographics: {'age': 40}\n\n"
    "Current internal state:\n"
    "- Support level: 0.50\n"
    "- Resistance level: 0.30\n"
    "- Workload stress: 0.40\n"
    "- Belief posture: strategic_support\n\n"
    "Stay in character. Use concise, policy-relevant language grounded in your role."
)

_GOLDEN_TIER2_PROMPT = (
    "You are Principal, acting as a principal in scenario 'psle_reform_mvp'.\n"
    "Prompt version: v1.\n"
    "Fidelity: Tier 2 (simplified persona — structural participation; omit deep biography).\n\n"
    "Position and stance:\n"
    "- Style cues: Formal.\n"
    "- Beliefs / policy position: {'k': 1}\n\n"
    "Current internal state:\n"
    "- Support level: 0.50\n"
    "- Resistance level: 0.30\n"
    "- Workload stress: 0.40\n"
    "- Belief posture: strategic_support\n\n"
    "Stay in character. Use concise, policy-relevant language grounded in your role."
)


def _scenario_with_sentinel_context() -> object:
    doc = scenario_config_to_document(get_scenario("psle_reform_mvp"))
    doc["scenario_id"] = "ctx_sentinel_test"
    doc["name"] = "Context Sentinel Test"
    doc["context"] = {"sentinel_phrase": SENTINEL}
    doc["personas"] = doc["personas"][:3]
    return scenario_from_mapping(doc)


def test_absent_context_byte_identical_tier1_prompt() -> None:
    assert build_system_prompt(**_GOLDEN_TIER1_KWARGS) == _GOLDEN_TIER1_PROMPT
    assert build_system_prompt(**_GOLDEN_TIER1_KWARGS, organisational_context={}) == _GOLDEN_TIER1_PROMPT
    assert build_system_prompt(**_GOLDEN_TIER1_KWARGS, organisational_context=None) == _GOLDEN_TIER1_PROMPT


def test_absent_context_byte_identical_tier2_prompt() -> None:
    assert (
        simplified_persona_prompt(
            scenario_id="psle_reform_mvp",
            role="principal",
            name="Principal",
            style_cues="Formal.",
            beliefs={"k": 1},
            state=_GOLDEN_TIER1_KWARGS["state"],
            prompt_version="v1",
        )
        == _GOLDEN_TIER2_PROMPT
    )


def test_malformed_context_raises_at_load() -> None:
    base = scenario_config_to_document(get_scenario("psle_reform_mvp"))
    base["personas"] = base["personas"][:1]
    for bad in ("not-a-dict", ["list"]):
        doc = {**base, "context": bad}
        with pytest.raises(ValueError, match="scenario.context must be a mapping"):
            scenario_from_mapping(doc)


def test_framing_line_and_order_tier1() -> None:
    system = build_system_prompt(
        **_GOLDEN_TIER1_KWARGS,
        organisational_context={"school_profile": "High-needs school."},
    )
    assert "not a policy event or instruction" in system
    assert ORGANISATIONAL_CONTEXT_TITLE in system
    assert system.index("not a policy event or instruction") < system.index("Persona identity and stance:")
    assert "school_profile" in system


def test_framing_line_and_order_tier2() -> None:
    system = simplified_persona_prompt(
        scenario_id="psle_reform_mvp",
        role="principal",
        name="Principal",
        style_cues="Formal.",
        beliefs={"k": 1},
        state=_GOLDEN_TIER1_KWARGS["state"],
        prompt_version="v1",
        organisational_context={"school_profile": "High-needs school."},
    )
    assert "not a policy event or instruction" in system
    assert system.index("not a policy event or instruction") < system.index("Position and stance:")


@pytest.mark.asyncio
async def test_sentinel_phrase_in_every_llm_system_prompt() -> None:
    cfg = _scenario_with_sentinel_context()
    personas = cfg.personas
    llm_calls: list[str] = []

    async def fake_llm_complete(**kwargs) -> str:
        llm_calls.append(kwargs["messages"][0]["content"])
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
            db_path = os.path.join(tmp, "ctx_sentinel.sqlite")
            await init_db(db_path)
            sim_id = await create_simulation_run(
                db_path,
                name="CtxSentinel",
                scenario_id=cfg.scenario_id,
                status="pending",
                total_rounds=1,
                random_seed=99,
                prompt_version="v1",
                model_used="fake",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id=cfg.scenario_id,
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
            assert len(llm_calls) == 2
            for prompt in llm_calls:
                assert SENTINEL in prompt
    finally:
        orchestrator.llm_complete = orig


@pytest.mark.asyncio
async def test_scenario_context_in_config_snapshot(tmp_path) -> None:
    from mirofish_backend.api import simulations as sim_api
    from mirofish_backend.api.simulations import SimulationRunRequest, queue_simulation_run
    from mirofish_backend.config import Settings

    doc = scenario_config_to_document(get_scenario("psle_reform_mvp"))
    doc["scenario_id"] = "ctx_snapshot_test"
    doc["personas"] = doc["personas"][:1]
    ctx = {"school_profile": "High-needs", "leadership_stability": "Three principals in six years."}
    doc["context"] = ctx
    cfg_with_ctx = scenario_from_mapping(doc)

    created: dict[str, object] = {}
    db_path = str(tmp_path / "ctx.sqlite")
    await init_db(db_path)

    async def fake_create(*_a, config_snapshot=None, **_kwargs):
        created["config_snapshot"] = config_snapshot
        return "sim-ctx-test"

    async def noop_guarded(**_kwargs):
        return None

    with (
        patch.object(sim_api, "create_simulation_run", side_effect=fake_create),
        patch.object(sim_api, "run_simulation_task_guarded", side_effect=noop_guarded),
        patch.object(sim_api.asyncio, "create_task", side_effect=lambda *_a, **_k: None),
        patch.object(sim_api, "load_scenario_for_run", return_value=(cfg_with_ctx, "user")),
    ):
        settings = Settings(sqlite_path=db_path)
        req = SimulationRunRequest(scenario_id=cfg_with_ctx.scenario_id, llm_provider="lmstudio")
        await queue_simulation_run(settings, req)

    snap = created.get("config_snapshot")
    assert isinstance(snap, dict)
    assert snap.get("scenario_context") == ctx


def test_builtin_scenarios_have_empty_context() -> None:
    for sid in ("psle_reform_mvp", "fsbb_comparator"):
        assert get_scenario(sid).context == {}
