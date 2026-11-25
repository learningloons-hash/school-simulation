"""
M-ROSTER independent tester — simulation integration tests (spec §12 A1, B, C, D, F, I).

Monkeypatches senna_backend.simulation.orchestrator.llm_complete.
Synthetic data only; no School-S or Ahn names.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import aiosqlite
import pytest

from senna_backend.db.repo import (
    create_simulation_run,
    get_simulation_status_with_transcript,
)
from senna_backend.db.schema import init_db
from senna_backend.llm.router import LLMCompletion
from senna_backend.scenarios.registry import scenario_from_mapping
from senna_backend.simulation import orchestrator
from senna_backend.simulation.roster_windows import resolve_activity_windows


# ---------------------------------------------------------------------------
# Shared scenario and fake-LLM helpers
# ---------------------------------------------------------------------------

# Support levels by agent slot index (used to vary alignment_index).
_SUPPORT_BY_SLOT = {0: 0.8, 1: 0.6, 2: 0.2, 3: 0.7}
_LIKERT_RESPONSE = json.dumps({"support": 3, "resistance": 2, "workload_stress": 4})


def _make_scenario(
    *,
    b_until: int | None = 2,
    c_from: int | None = 3,
    total_rounds: int = 4,
    with_handover: bool = True,
    absence_scope: str = "all_inactive",
    with_likert: bool = False,
) -> Any:
    """
    4-teacher synthetic scenario.
      Teacher A (teacher_a_000): role_level=1, active 1..total_rounds
      Teacher B (teacher_b_001): role_level=2, active_until_round=b_until (None = full)
      Teacher C (teacher_c_002): role_level=3, active_from_round=c_from (None = full)
      Teacher D (teacher_d_003): role_level=4, active 1..total_rounds
    """
    pe: dict[str, str] = {}
    for r in range(1, total_rounds + 1):
        pe[str(r)] = f"Policy event for round {r}."

    personas: list[dict] = [
        {
            "persona_id": "teacher_a",
            "role": "Principal",
            "name": "Teacher A",
            "role_level": 1,
            "style_cues": "Strategic.",
            "beliefs": {"support_policy": 0.6},
            "initial_state": {
                "support_level": _SUPPORT_BY_SLOT[0],
                "resistance_level": 0.3,
                "workload_stress": 0.5,
                "belief_posture": "supportive",
            },
        },
        {
            "persona_id": "teacher_b",
            "role": "HOD",
            "name": "Teacher B",
            "role_level": 2,
            "style_cues": "Operational.",
            "beliefs": {"support_policy": 0.5},
            "initial_state": {
                "support_level": _SUPPORT_BY_SLOT[1],
                "resistance_level": 0.3,
                "workload_stress": 0.5,
                "belief_posture": "neutral",
            },
        },
        {
            "persona_id": "teacher_c",
            "role": "Teacher",
            "name": "Teacher C",
            "role_level": 3,
            "style_cues": "Classroom-focused.",
            "beliefs": {"support_policy": 0.4},
            "initial_state": {
                "support_level": _SUPPORT_BY_SLOT[2],
                "resistance_level": 0.5,
                "workload_stress": 0.6,
                "belief_posture": "resistant",
            },
        },
        {
            "persona_id": "teacher_d",
            "role": "Senior Teacher",
            "name": "Teacher D",
            "role_level": 4,
            "style_cues": "Pragmatic.",
            "beliefs": {"support_policy": 0.7},
            "initial_state": {
                "support_level": _SUPPORT_BY_SLOT[3],
                "resistance_level": 0.3,
                "workload_stress": 0.5,
                "belief_posture": "supportive",
            },
        },
    ]
    if b_until is not None:
        personas[1]["active_until_round"] = b_until
        personas[1]["absence_reason"] = "on leave"
    if c_from is not None:
        personas[2]["active_from_round"] = c_from

    rw: dict[str, Any] = {"absence_notice_scope": absence_scope}
    if with_handover:
        rw["handover_template"] = (
            "Welcome, {name}. You join at round {join_round} of {total_rounds}. "
            "This round: {join_policy_event}"
        )

    raw: dict[str, Any] = {
        "scenario_id": "test_roster_scenario",
        "name": "Test Roster Scenario",
        "policy_events": pe,
        "personas": personas,
        "roster_windows": rw,
    }
    if with_likert:
        labels6 = ["Strongly Disagree", "Disagree", "Slightly Disagree",
                   "Slightly Agree", "Agree", "Strongly Agree"]
        raw["likert_self_report_enabled"] = True
        raw["likert_anchor_labels"] = {
            "support": labels6,
            "resistance": labels6,
            "workload_stress": ["Very Low", "Low", "Below Average",
                                "Above Average", "High", "Very High"],
        }
    return scenario_from_mapping(raw)


# Agent IDs derived from persona_id + slot index
_AID_A = "teacher_a_000"
_AID_B = "teacher_b_001"
_AID_C = "teacher_c_002"
_AID_D = "teacher_d_003"


def _make_fake_llm(calls: list[dict]) -> Any:
    """Return a fake llm_complete that records calls and returns valid state+sentinel."""

    async def fake_llm(*, messages: list[dict], llm_request_context: dict | None = None, **kw) -> LLMCompletion:
        ctx = llm_request_context or {}
        rn = ctx.get("round_number", 0)
        aid = ctx.get("agent_id", "?")
        call_site = ctx.get("call_site", "")
        calls.append({"messages": [m.copy() for m in messages], "context": dict(ctx)})
        if call_site == "likert_round_end":
            return LLMCompletion(
                text=f"<likert>{_LIKERT_RESPONSE}</likert>",
                input_tokens=5,
                output_tokens=5,
            )
        # Vary support_level by slot so alignment_index differs when inactive agent included
        slot = int(aid.split("_")[-1]) if aid != "?" else 0
        support = _SUPPORT_BY_SLOT.get(slot, 0.5)
        state = {
            "support_level": support,
            "resistance_level": 0.3,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        sentinel = f"SENTINEL-r{rn}-a{aid}"
        return LLMCompletion(
            text=f"Response. {sentinel}\n\n<state>\n{json.dumps(state)}\n</state>",
            input_tokens=10,
            output_tokens=10,
        )

    return fake_llm


def _base_run_kwargs(
    db_path: str,
    sim_id: str,
    *,
    total_rounds: int = 4,
    transcript_dir: str = "/tmp/transcripts",
    extra: dict | None = None,
) -> dict:
    kw = dict(
        sqlite_path=db_path,
        simulation_id=sim_id,
        scenario_id="test_roster_scenario",
        total_rounds=total_rounds,
        agent_limit=4,
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
        round_summary_enabled=True,
        transcript_dir=transcript_dir,
        llm_concurrency_cap=1,
    )
    if extra:
        kw.update(extra)
    return kw


# ---------------------------------------------------------------------------
# §A1 — Byte-identical default
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_byte_identical_explicit_full_windows(monkeypatch, tmp_path) -> None:
    """
    §A1: psle_reform_mvp with every actor windowed 1..R is identical to no windows.
    Checks: turn sequence, prompts, global snapshot values, config_snapshot keys.
    """
    from senna_backend.scenarios.registry import get_scenario

    scenario = get_scenario("psle_reform_mvp")
    total_rounds = 2
    agent_limit = 2
    transcript_dir = str(tmp_path / "transcripts")

    # Build windowed version: every actor active 1..total_rounds
    from senna_backend.scenarios.registry import PersonaTemplate

    windowed_personas = [
        PersonaTemplate(
            persona_id=p.persona_id,
            role=p.role,
            name=p.name,
            role_level=p.role_level,
            style_cues=p.style_cues,
            beliefs=dict(p.beliefs),
            groups=p.groups,
            initial_state=dict(p.initial_state),
            implementation_posture=p.implementation_posture,
            active_from_round=1,
            active_until_round=total_rounds,
        )
        for p in (
            __import__("senna_backend.roster.csv_roster", fromlist=["personas_for_run"])
            .personas_for_run(scenario, agent_limit, None)
        )
    ]
    from senna_backend.scenarios.registry import ScenarioConfig

    windowed_scenario = ScenarioConfig(
        scenario_id="psle_reform_mvp",
        name=scenario.name,
        policy_events=scenario.policy_events,
        personas=windowed_personas,
        groups=scenario.groups,
        rag_enabled=False,
        likert_self_report_enabled=False,
        roster_windows=None,  # no roster_windows block → gating off
    )

    async def _run_one(scenario_cfg, seed_extra: int = 0) -> tuple[dict, list[dict]]:
        calls: list[dict] = []
        fake = _make_fake_llm(calls)
        monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", fake)
        db = tmp_path / f"sim_{seed_extra}.sqlite"
        await init_db(str(db))
        sim_id = await create_simulation_run(
            str(db), name="A1test", scenario_id="psle_reform_mvp",
            status="pending", total_rounds=total_rounds,
            random_seed=42, prompt_version="v0", model_used="fake",
        )
        await orchestrator.run_simulation_task(
            sqlite_path=str(db),
            simulation_id=sim_id,
            scenario_id="psle_reform_mvp",
            scenario_config=scenario_cfg,
            total_rounds=total_rounds,
            agent_limit=agent_limit,
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
            round_summary_enabled=False,
            llm_concurrency_cap=1,
        )
        result = await get_simulation_status_with_transcript(str(db), simulation_id=sim_id)
        return result, calls

    # Run with original scenario (no windows)
    res_base, calls_base = await _run_one(scenario)
    # Run with windowed scenario (every actor 1..R)
    res_win, calls_win = await _run_one(windowed_scenario, seed_extra=1)

    assert res_base["status"] == "completed"
    assert res_win["status"] == "completed"

    # Turn sequence identical
    base_seq = [(t["round_number"], t["turn_index"], t["agent_id"],
                 t["interaction_type"]) for t in res_base["transcript"]]
    win_seq = [(t["round_number"], t["turn_index"], t["agent_id"],
                t["interaction_type"]) for t in res_win["transcript"]]
    assert base_seq == win_seq

    # Prompts identical (user messages from agent_turn calls)
    base_user = [c["messages"][-1]["content"] for c in calls_base if c["context"].get("call_site") == "agent_turn"]
    win_user = [c["messages"][-1]["content"] for c in calls_win if c["context"].get("call_site") == "agent_turn"]
    assert base_user == win_user

    # config_snapshot keys: windowed scenario (all 1..R, windowing_active=False) → no roster_windows key
    assert "roster_windows" not in (res_base["config_snapshot"] or {})
    assert "roster_windows" not in (res_win["config_snapshot"] or {})

    # State timeline identical (same support/resistance values)
    base_tl = res_base["state_timeline"]
    win_tl = res_win["state_timeline"]
    assert len(base_tl) == len(win_tl)
    for b, w in zip(base_tl, win_tl):
        for agent_b, agent_w in zip(b["agents"], w["agents"]):
            assert abs(agent_b["support_level"] - agent_w["support_level"]) < 1e-9


# ---------------------------------------------------------------------------
# §B1 — Windowed actor only speaks in its window
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_windowed_actor_only_speaks_in_window(monkeypatch, tmp_path) -> None:
    """Teacher B active rounds 1..2, Teacher C active rounds 3..4; check DB turns."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "b1.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="B1", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )
    result = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    assert result["status"] == "completed"

    turns = result["transcript"]
    # Teacher B only in rounds 1–2
    b_rounds = {t["round_number"] for t in turns if t["agent_id"] == _AID_B}
    assert b_rounds == {1, 2}, f"Teacher B spoke in unexpected rounds: {b_rounds}"

    # Teacher C only in rounds 3–4
    c_rounds = {t["round_number"] for t in turns if t["agent_id"] == _AID_C}
    assert c_rounds == {3, 4}, f"Teacher C spoke in unexpected rounds: {c_rounds}"

    # No LLM call for Teacher B outside rounds 1–2
    b_llm_rounds = {c["context"]["round_number"] for c in calls
                    if c["context"].get("agent_id") == _AID_B
                    and c["context"].get("call_site") == "agent_turn"}
    assert b_llm_rounds.issubset({1, 2}), f"LLM called for B outside window: {b_llm_rounds}"


# ---------------------------------------------------------------------------
# §B2 — sample_k picks only active agents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sample_k_active_agents_only(monkeypatch, tmp_path) -> None:
    """With sample_k_per_round, inactive agents are never picked."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "b2.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="B2", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=99, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir, extra={
            "simulation_mode": "sample_k_per_round",
            "speakers_per_round": 2,
            "random_seed": 99,
        }),
        scenario_config=scenario,
    )
    result = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    assert result["status"] == "completed"

    turns = result["transcript"]
    # Teacher C never speaks in rounds 1–2
    for t in turns:
        if t["round_number"] in (1, 2):
            assert t["agent_id"] != _AID_C, "Teacher C (inactive) spoke in round 1 or 2"
    # Teacher B never speaks in rounds 3–4
    for t in turns:
        if t["round_number"] in (3, 4):
            assert t["agent_id"] != _AID_B, "Teacher B (inactive) spoke in round 3 or 4"

    # Deterministic: same seed, same picks (run again, compare sequence)
    db2 = str(tmp_path / "b2b.sqlite")
    calls2: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls2))
    await init_db(db2)
    sim_id2 = await create_simulation_run(
        db2, name="B2b", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=99, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db2, sim_id2, transcript_dir=tdir, extra={
            "simulation_mode": "sample_k_per_round",
            "speakers_per_round": 2,
            "random_seed": 99,
        }),
        scenario_config=scenario,
    )
    result2 = await get_simulation_status_with_transcript(db2, simulation_id=sim_id2)
    seq1 = [(t["round_number"], t["agent_id"]) for t in turns]
    seq2 = [(t["round_number"], t["agent_id"]) for t in result2["transcript"]]
    assert seq1 == seq2, "sample_k not deterministic across two runs with same seed"


# ---------------------------------------------------------------------------
# §B3 — hierarchical order among active agents, no reply to inactive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hierarchical_order_active_subset(monkeypatch, tmp_path) -> None:
    """With turn_order_policy=hierarchical, active agents speak in role_level order."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "b3.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="B3", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir, extra={"turn_order_policy": "hierarchical"}),
        scenario_config=scenario,
    )
    result = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    assert result["status"] == "completed"

    turns = result["transcript"]
    # Round 1: active = A(rl=1), B(rl=2), D(rl=4). First turn should be A.
    r1 = [t for t in turns if t["round_number"] == 1]
    assert r1[0]["agent_id"] == _AID_A, "In round 1, Teacher A (rl=1) should speak first"

    # Round 3: active = A(rl=1), C(rl=3), D(rl=4). First turn should be A.
    r3 = [t for t in turns if t["round_number"] == 3]
    assert r3[0]["agent_id"] == _AID_A, "In round 3, Teacher A (rl=1) should speak first"

    # No reply targets Teacher B in rounds 3–4 (B inactive)
    for t in turns:
        if t["round_number"] in (3, 4) and t["interaction_type"] == "reply":
            assert t["target_agent_id"] != _AID_B, \
                f"Reply to inactive Teacher B in round {t['round_number']}"

    # No reply targets Teacher C in rounds 1–2 (C inactive)
    for t in turns:
        if t["round_number"] in (1, 2) and t["interaction_type"] == "reply":
            assert t["target_agent_id"] != _AID_C, \
                f"Reply to inactive Teacher C in round {t['round_number']}"


# ---------------------------------------------------------------------------
# §B4 — zero active agents raises ValueError (tested via resolve_activity_windows)
# ---------------------------------------------------------------------------

def test_zero_active_agents_raises_in_resolve() -> None:
    """resolve_activity_windows raises ValueError for a round with zero active agents."""
    from senna_backend.scenarios.registry import PersonaTemplate

    personas = [
        PersonaTemplate(
            persona_id="a", role="r", name="N", role_level=1, style_cues="", beliefs={},
            active_from_round=1, active_until_round=1,
        ),
        PersonaTemplate(
            persona_id="b", role="r", name="M", role_level=2, style_cues="", beliefs={},
            active_from_round=3, active_until_round=4,
        ),
    ]
    with pytest.raises(ValueError, match="round 2 has no active agents"):
        resolve_activity_windows(["a", "b"], personas, total_rounds=4)


# ---------------------------------------------------------------------------
# §C1-C5 — Newcomer information rule
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_newcomer_information_rule(monkeypatch, tmp_path) -> None:
    """
    §C1: In join round J (3), newcomer prompt:
      - no SENTINEL from rounds < J
      - working memory "- (none)"
      - no "Prior rounds" summaries block
    §C2: In round J+1 (4), newcomer sees round-J content, no pre-J content.
    §C3: Round-1 agent (Teacher A) still gets pre-J summaries.
    §C4: Newcomer's Likert prompt in J has no pre-J sentinel.
    §C5: memory_context inclusion log has pre_join exclusions.
    """
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4, with_likert=True)
    db = str(tmp_path / "c_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="C-test", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir, extra={"likert_self_report_enabled": True}),
        scenario_config=scenario,
    )
    result = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    assert result["status"] == "completed"

    # Find Teacher C's turn in round 3 (join round)
    c_r3_calls = [c for c in calls
                  if c["context"].get("agent_id") == _AID_C
                  and c["context"].get("round_number") == 3
                  and c["context"].get("call_site") == "agent_turn"]
    assert len(c_r3_calls) >= 1, "Teacher C should have an agent_turn call in round 3"

    c_r3_prompt = c_r3_calls[0]["messages"][-1]["content"]  # user message

    # §C1a: no sentinel from rounds 1 or 2 in C's round-3 prompt
    assert "SENTINEL-r1-a" not in c_r3_prompt, "Pre-join round-1 sentinel found in newcomer's round-3 prompt"
    assert "SENTINEL-r2-a" not in c_r3_prompt, "Pre-join round-2 sentinel found in newcomer's round-3 prompt"

    # §C1b: working memory "- (none)" (C has no prior turns before round 3)
    assert "- (none)" in c_r3_prompt, "Newcomer working memory should be '- (none)' in join round"

    # §C1c: no "Prior rounds — compact summaries" block
    assert "Prior rounds — compact summaries" not in c_r3_prompt, \
        "Newcomer should not see prior-round summaries in join round"

    # §C2: Teacher C in round 4 should see round-3 content, no pre-J content
    c_r4_calls = [c for c in calls
                  if c["context"].get("agent_id") == _AID_C
                  and c["context"].get("round_number") == 4
                  and c["context"].get("call_site") == "agent_turn"]
    assert len(c_r4_calls) >= 1
    c_r4_prompt = c_r4_calls[0]["messages"][-1]["content"]

    # Round 3 sentinel should appear (via summary or peer turns)
    assert "SENTINEL-r3-a" in c_r4_prompt, "Newcomer should see round-3 content in round 4"
    # No round-1 or round-2 sentinels
    assert "SENTINEL-r1-a" not in c_r4_prompt
    assert "SENTINEL-r2-a" not in c_r4_prompt

    # §C3: Teacher A (always active from round 1) in round 4 should see pre-J summaries
    a_r4_calls = [c for c in calls
                  if c["context"].get("agent_id") == _AID_A
                  and c["context"].get("round_number") == 4
                  and c["context"].get("call_site") == "agent_turn"]
    assert len(a_r4_calls) >= 1
    a_r4_prompt = a_r4_calls[0]["messages"][-1]["content"]
    # Teacher A should see round-1 content (via summaries)
    assert "Prior rounds — compact summaries" in a_r4_prompt, \
        "Teacher A (always active) should see prior-round summaries"
    # Round 1 or 2 sentinels should appear in A's round-4 prompt (via summaries)
    has_pre_j = "SENTINEL-r1-a" in a_r4_prompt or "SENTINEL-r2-a" in a_r4_prompt
    assert has_pre_j, "Teacher A should see pre-J round content in round 4"

    # §C4: Newcomer's Likert prompt in round 3 should have no pre-J sentinel
    c_r3_likert_calls = [c for c in calls
                         if c["context"].get("agent_id") == _AID_C
                         and c["context"].get("round_number") == 3
                         and c["context"].get("call_site") == "likert_round_end"]
    if c_r3_likert_calls:
        likert_prompt = c_r3_likert_calls[0]["messages"][-1]["content"]
        assert "SENTINEL-r1-a" not in likert_prompt
        assert "SENTINEL-r2-a" not in likert_prompt

    # §C5: memory context log has pre_join exclusions for Teacher C
    async with aiosqlite.connect(db) as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM agent_context_inclusion "
            "WHERE simulation_id=? AND observer_agent_id=? AND exclusion_reason='pre_join'",
            (sim_id, _AID_C),
        )
        row = await cur.fetchone()
        assert row is not None and row[0] > 0, \
            "No pre_join exclusions logged for Teacher C"


# ---------------------------------------------------------------------------
# §D1, D2, D4 — Handover note
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handover_note_in_join_round_only(monkeypatch, tmp_path) -> None:
    """
    §D1: Newcomer's round-J prompt has handover note with rendered placeholders.
         It's absent from round J+1, from other agents, and from Likert prompts.
    §D2: Without a template, no handover block appears.
    §D4: config_snapshot.roster_windows.handover_notes[agent_id] = rendered text.
    """
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4, with_handover=True, with_likert=True)
    db = str(tmp_path / "d_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="D-test", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir, extra={"likert_self_report_enabled": True}),
        scenario_config=scenario,
    )
    result = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    assert result["status"] == "completed"

    # Find Teacher C's round-3 agent_turn prompt
    c_r3_call = next(
        (c for c in calls if c["context"].get("agent_id") == _AID_C
         and c["context"].get("round_number") == 3
         and c["context"].get("call_site") == "agent_turn"),
        None,
    )
    assert c_r3_call is not None
    c_r3_prompt = c_r3_call["messages"][-1]["content"]

    # §D1a: handover note present in join round
    assert "Handover note (given to you on joining; only you can see this):" in c_r3_prompt
    assert "Teacher C" in c_r3_prompt  # {name} rendered
    assert "round 3 of 4" in c_r3_prompt  # {join_round}/{total_rounds} rendered
    assert "Policy event for round 3" in c_r3_prompt  # {join_policy_event} rendered

    # §D1b: absent from round J+1
    c_r4_call = next(
        (c for c in calls if c["context"].get("agent_id") == _AID_C
         and c["context"].get("round_number") == 4
         and c["context"].get("call_site") == "agent_turn"),
        None,
    )
    assert c_r4_call is not None
    assert "Handover note" not in c_r4_call["messages"][-1]["content"]

    # §D1c: absent from other agents (Teacher A in round 3)
    a_r3_call = next(
        (c for c in calls if c["context"].get("agent_id") == _AID_A
         and c["context"].get("round_number") == 3
         and c["context"].get("call_site") == "agent_turn"),
        None,
    )
    assert a_r3_call is not None
    assert "Handover note" not in a_r3_call["messages"][-1]["content"]

    # §D1d: absent from Likert prompts
    for c in calls:
        if c["context"].get("call_site") == "likert_round_end":
            assert "Handover note" not in c["messages"][-1]["content"]

    # §D4: config_snapshot.roster_windows.handover_notes[agent_id] = rendered text
    cfg = result["config_snapshot"]
    assert cfg is not None
    rw_snap = cfg.get("roster_windows")
    assert rw_snap is not None, "roster_windows absent from config_snapshot"
    handover_notes = rw_snap.get("handover_notes", {})
    assert _AID_C in handover_notes, "handover_notes missing Teacher C's agent_id"
    note = handover_notes[_AID_C]
    assert "Teacher C" in note
    assert "3 of 4" in note


@pytest.mark.asyncio
async def test_no_handover_without_template(monkeypatch, tmp_path) -> None:
    """§D2: No handover block when template is absent."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4, with_handover=False)
    db = str(tmp_path / "d2_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="D2", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )
    for c in calls:
        assert "Handover note" not in c["messages"][-1]["content"]


# ---------------------------------------------------------------------------
# §F1 — No Likert rows for inactive agents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_likert_rows_for_inactive(monkeypatch, tmp_path) -> None:
    """§F1: No agent_round_likert rows for inactive (agent, round) pairs."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4, with_likert=True)
    db = str(tmp_path / "f1_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="F1", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir, extra={"likert_self_report_enabled": True}),
        scenario_config=scenario,
    )

    async with aiosqlite.connect(db) as conn:
        # Teacher B inactive in rounds 3,4 → should have NO rows there
        cur = await conn.execute(
            "SELECT COUNT(*) FROM agent_round_likert "
            "WHERE simulation_id=? AND agent_id=? AND round_number IN (3,4)",
            (sim_id, _AID_B),
        )
        row = await cur.fetchone()
        assert row[0] == 0, f"Teacher B has Likert rows in inactive rounds: {row[0]}"

        # Teacher C inactive in rounds 1,2 → should have NO rows there
        cur2 = await conn.execute(
            "SELECT COUNT(*) FROM agent_round_likert "
            "WHERE simulation_id=? AND agent_id=? AND round_number IN (1,2)",
            (sim_id, _AID_C),
        )
        row2 = await cur2.fetchone()
        assert row2[0] == 0, f"Teacher C has Likert rows in inactive rounds: {row2[0]}"

        # Teacher B should have rows in rounds 1,2
        cur3 = await conn.execute(
            "SELECT COUNT(*) FROM agent_round_likert "
            "WHERE simulation_id=? AND agent_id=? AND round_number IN (1,2)",
            (sim_id, _AID_B),
        )
        row3 = await cur3.fetchone()
        assert row3[0] > 0, "Teacher B should have Likert rows in its active rounds"


# ---------------------------------------------------------------------------
# §F2 — alignment_index uses active agents only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_alignment_index_active_agents_only(monkeypatch, tmp_path) -> None:
    """
    §F2: alignment_index = 1 - (max - min) over ACTIVE agents' support levels.
    Including Teacher C (support=0.2) in round 1 would change it.
    Active in round 1: A(0.8), B(0.6), D(0.7). Spread = 0.8-0.6 = 0.2.
    If C (0.2) included: spread = 0.8-0.2 = 0.6.
    """
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "f2_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="F2", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )
    result = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    assert result["status"] == "completed"

    # alignment_index after round 1 (active: A=0.8, B=0.6, D=0.7)
    tl = result["state_timeline"]
    r1_entry = next((t for t in tl if t.get("round_number") == 1), None)
    assert r1_entry is not None
    gs_r1 = r1_entry["global_state"]
    ai_r1 = gs_r1.get("alignment_index")
    assert ai_r1 is not None

    # Spread over active = max(0.8,0.6,0.7) - min(0.8,0.6,0.7) = 0.8 - 0.6 = 0.2
    # alignment_index = 1 - 0.2 = 0.8
    expected_active = 1.0 - (0.8 - 0.6)
    # alignment_index with C (0.2) would be: 1 - (0.8-0.2) = 0.4
    expected_with_inactive = 1.0 - (0.8 - 0.2)
    assert abs(ai_r1 - expected_active) < 0.05, \
        f"alignment_index {ai_r1:.3f} ≠ expected {expected_active:.3f} (active only)"
    assert abs(ai_r1 - expected_with_inactive) > 0.1, \
        "alignment_index matches the wrong value (including inactive agent)"


# ---------------------------------------------------------------------------
# §F3 — convergence_delta active-both-rounds only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_convergence_delta_active_both_rounds(monkeypatch, tmp_path) -> None:
    """
    §F3: convergence_delta at round r averages only agents active in both r-1 and r.
    In round 3: Teacher B was active in round 2 but not in round 3 → excluded.
    Teacher C active in round 3 but not round 2 → excluded.
    Only A and D contribute.
    """
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "f3_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="F3", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )
    result = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    assert result["status"] == "completed"

    tl = result["state_timeline"]
    # Round 3 conv_delta: should be computed from A and D only (no B, no C)
    r3 = next((t for t in tl if t.get("round_number") == 3), None)
    assert r3 is not None
    # convergence_delta lives in the nested global_state dict
    gs_r3 = r3["global_state"]
    # conv_delta is not None because A and D are active in both rounds 2 and 3
    assert gs_r3.get("convergence_delta") is not None, \
        "convergence_delta should be non-None in round 3 (A and D are active in both rounds)"

    # For a round where NO agent is active in both r-1 and r:
    # This would require a scenario where the transition between rounds has no overlap.
    # With our scenario (A always active), this won't be None. But we can test the pure function:
    from senna_backend.simulation.roster_windows import agents_active_both_rounds, ActivityWindow

    class FakeAg:
        def __init__(self, aid): self.agent_id = aid

    wins = {
        "x": ActivityWindow("x", 1, 1, "", ""),
        "y": ActivityWindow("y", 2, 4, "", ""),
    }
    result_empty = agents_active_both_rounds([FakeAg("x"), FakeAg("y")], wins, round_number=2)
    assert result_empty == [], "No agent active in both round 1 and 2 → empty"


# ---------------------------------------------------------------------------
# §F4 — No snapshot rows for inactive agents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshots_inactive_agents_absent(monkeypatch, tmp_path) -> None:
    """§F4: agent_state_snapshots has no rows for inactive (agent, round) pairs."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "f4_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="F4", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )

    async with aiosqlite.connect(db) as conn:
        # Teacher B inactive in rounds 3,4 → no snapshots
        cur = await conn.execute(
            "SELECT COUNT(*) FROM agent_state_snapshots "
            "WHERE simulation_id=? AND agent_id=? AND round_number IN (3,4)",
            (sim_id, _AID_B),
        )
        assert (await cur.fetchone())[0] == 0, "Inactive Teacher B has snapshot rows"

        # Teacher C inactive in rounds 1,2 → no snapshots
        cur2 = await conn.execute(
            "SELECT COUNT(*) FROM agent_state_snapshots "
            "WHERE simulation_id=? AND agent_id=? AND round_number IN (1,2)",
            (sim_id, _AID_C),
        )
        assert (await cur2.fetchone())[0] == 0, "Inactive Teacher C has snapshot rows"

        # Teacher A and D should have snapshots in all 4 rounds
        cur3 = await conn.execute(
            "SELECT COUNT(*) FROM agent_state_snapshots "
            "WHERE simulation_id=? AND agent_id=?",
            (sim_id, _AID_A),
        )
        assert (await cur3.fetchone())[0] == 4, "Teacher A should have 4 snapshot rows"


# ---------------------------------------------------------------------------
# §F5 — Leaver's earlier turns still in DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_leaver_turns_remain_in_db(monkeypatch, tmp_path) -> None:
    """§F5: Teacher B's turns from rounds 1–2 remain after the run."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "f5_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="F5", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )

    async with aiosqlite.connect(db) as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM agent_turns "
            "WHERE simulation_id=? AND agent_id=? AND round_number IN (1,2)",
            (sim_id, _AID_B),
        )
        count = (await cur.fetchone())[0]
        assert count >= 2, f"Teacher B's turns from rounds 1–2 should still be in DB, got {count}"


# ---------------------------------------------------------------------------
# §I1, I2, I3 — Export and transcript
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_active_agents_per_round_csv(monkeypatch, tmp_path) -> None:
    """§I1: zip has active_agents_per_round.csv with correct columns; absent without windows."""
    from senna_backend.db.repo import get_simulation_export_bundle
    from senna_backend.export_bundle import build_export_zip
    import zipfile
    import io

    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "i1_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="I1", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )

    bundle = await get_simulation_export_bundle(db, simulation_id=sim_id)
    assert bundle is not None
    zip_bytes = build_export_zip(bundle)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        members = zf.namelist()
        assert "active_agents_per_round.csv" in members, \
            f"active_agents_per_round.csv missing; members: {members}"

        content = zf.read("active_agents_per_round.csv").decode()
        lines = [l for l in content.strip().splitlines() if l.strip()]
        header = lines[0]
        assert "joined_agent_ids" in header
        assert "left_agent_ids" in header
        assert "inactive_agent_ids" in header

        # Round 3 row: Teacher C joined, Teacher B left
        r3_line = next((l for l in lines[1:] if l.startswith("3,")), None)
        assert r3_line is not None, "No round 3 row in active_agents_per_round.csv"
        assert _AID_C in r3_line, "Teacher C not in joined for round 3"
        assert _AID_B in r3_line, "Teacher B not in left for round 3"

    # §I1 (no windows): active_agents_per_round.csv absent
    db2 = str(tmp_path / "i1_nowin.sqlite")
    await init_db(db2)
    sim_id2 = await create_simulation_run(
        db2, name="I1NoWin", scenario_id="psle_reform_mvp",
        status="pending", total_rounds=1, random_seed=42, prompt_version="v0", model_used="fake",
    )
    calls2: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls2))
    await orchestrator.run_simulation_task(
        sqlite_path=db2, simulation_id=sim_id2, scenario_id="psle_reform_mvp",
        total_rounds=1, agent_limit=2, random_seed=42, prompt_version="v0", model_used="fake",
        lmstudio_model="fake", lmstudio_base_url="http://unused",
        llm_temperature=0.0, llm_max_tokens=256, working_memory_last_k=2,
        llm_provider="lmstudio", anthropic_api_key="", anthropic_model="unused",
        peer_context_max_chars=1200, rag_effective=False, embedding_model="unused",
        rag_top_k=4, rag_chunk_size=400, rag_chunk_overlap=80, rag_max_inject_chars=2400,
        round_summary_enabled=False, llm_concurrency_cap=1,
    )
    bundle2 = await get_simulation_export_bundle(db2, simulation_id=sim_id2)
    assert bundle2 is not None
    zip2 = build_export_zip(bundle2)
    with zipfile.ZipFile(io.BytesIO(zip2)) as zf2:
        assert "active_agents_per_round.csv" not in zf2.namelist()


@pytest.mark.asyncio
async def test_transcript_active_rounds_column(monkeypatch, tmp_path) -> None:
    """§I2: transcript header has 'Active rounds' column; each round has membership line."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "i2_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="I2", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )

    transcript_path = os.path.join(tdir, f"{sim_id}.md")
    assert os.path.exists(transcript_path), "Transcript file not created"
    content = open(transcript_path, encoding="utf-8").read()

    # §I2a: 'Active rounds' column in roster header
    assert "| Active rounds |" in content

    # §I2b: membership lines (*Active: ...*) present in each round section
    assert "*Active:" in content


@pytest.mark.asyncio
async def test_roster_window_audit_no_violations(monkeypatch, tmp_path) -> None:
    """§I3: roster_window_audit.turns_outside_window == 0."""
    calls: list[dict] = []
    monkeypatch.setattr("senna_backend.simulation.orchestrator.llm_complete", _make_fake_llm(calls))

    scenario = _make_scenario(b_until=2, c_from=3, total_rounds=4)
    db = str(tmp_path / "i3_test.sqlite")
    tdir = str(tmp_path / "transcripts")
    await init_db(db)
    sim_id = await create_simulation_run(
        db, name="I3", scenario_id="test_roster_scenario",
        status="pending", total_rounds=4, random_seed=42, prompt_version="v0", model_used="fake",
    )
    await orchestrator.run_simulation_task(
        **_base_run_kwargs(db, sim_id, transcript_dir=tdir),
        scenario_config=scenario,
    )
    result = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    cfg = result["config_snapshot"] or {}
    audit = cfg.get("roster_window_audit")
    assert audit is not None, "roster_window_audit missing from config_snapshot"
    assert audit["turns_outside_window"] == 0, \
        f"turns_outside_window = {audit['turns_outside_window']}, expected 0"
