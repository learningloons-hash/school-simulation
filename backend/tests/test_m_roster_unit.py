"""
M-ROSTER independent tester — unit tests (spec §12 A2, D3, E, G, J).

Pure-function tests only: no DB, no orchestrator, no live LLM calls.
Synthetic data only; no School-S or Ahn names.
"""

from __future__ import annotations

import random

import pytest

from senna_backend.roster.tenure_draw import draw_tenure_windows
from senna_backend.simulation.roster_windows import (
    ActivityWindow,
    absence_notice_for_round,
    active_agents_per_round_rows,
    agents_active_both_rounds,
    filter_turns_min_round,
    is_active,
    join_round,
    render_handover_note,
    resolve_activity_windows,
    roster_windows_config_snapshot,
    validate_handover_template,
    windowing_active,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _win(agent_id: str, *, frm: int = 1, until: int = 4) -> ActivityWindow:
    return ActivityWindow(
        agent_id=agent_id,
        active_from_round=frm,
        active_until_round=until,
        absence_reason="",
        window_basis="",
    )


# ---------------------------------------------------------------------------
# §D3 — validate_handover_template
# ---------------------------------------------------------------------------

def test_validate_handover_template_known_placeholders_all_pass() -> None:
    tmpl = "Hi {name} ({role}). Round {join_round}/{total_rounds}. Event: {join_policy_event}."
    assert validate_handover_template(tmpl) == []


def test_validate_handover_template_unknown_placeholder_returns_error() -> None:
    errors = validate_handover_template("Hello {name}, your {unknown_key} is set.")
    assert len(errors) == 1
    assert "unknown_key" in errors[0]


def test_validate_handover_template_literal_braces_pass() -> None:
    tmpl = "Use {{literal}} braces, {name}."
    assert validate_handover_template(tmpl) == []


def test_validate_handover_template_multiple_unknowns() -> None:
    errors = validate_handover_template("{foo} and {bar} and {name}")
    assert len(errors) == 2
    keys = " ".join(errors)
    assert "foo" in keys
    assert "bar" in keys


def test_validate_handover_template_empty_passes() -> None:
    assert validate_handover_template("") == []


# ---------------------------------------------------------------------------
# §A2 (pure part) — build_user_prompt with/without new kwargs
# ---------------------------------------------------------------------------

def test_build_user_prompt_no_new_kwargs_no_handover_no_notice() -> None:
    from senna_backend.llm.prompt_templates import build_user_prompt

    result = build_user_prompt(
        round_number=1,
        policy_event="Policy A.",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_name=None,
        intent_tag="discuss",
        prior_agent_memory=[],
        recent_interactions=[],
    )
    assert "Handover note" not in result
    assert "Not present this round" not in result


def test_build_user_prompt_explicit_none_kwargs_identical_to_omitted() -> None:
    from senna_backend.llm.prompt_templates import build_user_prompt

    base_kwargs = dict(
        round_number=2,
        policy_event="Policy B.",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_name=None,
        intent_tag="discuss",
        prior_agent_memory=["- prior line"],
        recent_interactions=[],
    )
    without_new = build_user_prompt(**base_kwargs)
    with_none = build_user_prompt(**base_kwargs, handover_note=None, absence_notice=None)
    assert without_new == with_none


def test_build_user_prompt_handover_note_appears() -> None:
    from senna_backend.llm.prompt_templates import build_user_prompt

    result = build_user_prompt(
        round_number=3,
        policy_event="Policy C.",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_name=None,
        intent_tag="discuss",
        prior_agent_memory=[],
        recent_interactions=[],
        handover_note="Welcome to round 3.",
    )
    assert "Handover note (given to you on joining; only you can see this):" in result
    assert "Welcome to round 3." in result


def test_build_user_prompt_absence_notice_appears() -> None:
    from senna_backend.llm.prompt_templates import build_user_prompt

    result = build_user_prompt(
        round_number=2,
        policy_event="Policy D.",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_name=None,
        intent_tag="discuss",
        prior_agent_memory=[],
        recent_interactions=[],
        absence_notice="Not present this round: Teacher B (on leave).",
    )
    assert "Not present this round: Teacher B (on leave)." in result


# ---------------------------------------------------------------------------
# §E — absence notice
# ---------------------------------------------------------------------------

def _make_windows_and_agents() -> tuple[dict[str, ActivityWindow], dict[str, tuple[str, str]], list[str]]:
    """4 agents: A always active, B leaves after round 2, C joins at round 3, D always active."""
    windows = {
        "agent_a": _win("agent_a", frm=1, until=4),
        "agent_b": ActivityWindow("agent_b", 1, 2, "on leave", ""),
        "agent_c": ActivityWindow("agent_c", 3, 4, "", ""),
        "agent_d": _win("agent_d", frm=1, until=4),
    }
    agents_by_id = {
        "agent_a": ("Teacher A", "Principal"),
        "agent_b": ("Teacher B", "HOD"),
        "agent_c": ("Teacher C", "Teacher"),
        "agent_d": ("Teacher D", "Senior Teacher"),
    }
    ordered = ["agent_a", "agent_b", "agent_c", "agent_d"]
    return windows, agents_by_id, ordered


def test_absence_notice_all_inactive_round1() -> None:
    """In round 1, Teacher C not yet joined → absent."""
    windows, agents_by_id, ordered = _make_windows_and_agents()
    notice = absence_notice_for_round(windows, agents_by_id, ordered, round_number=1, scope="all_inactive")
    assert notice is not None
    assert "Teacher C" in notice
    # Teacher B is active in round 1 → not in notice
    assert "Teacher B" not in notice
    # No reason for Teacher C
    assert "(on leave)" not in notice


def test_absence_notice_all_inactive_round3() -> None:
    """In round 3, Teacher B has left (absence_reason='on leave')."""
    windows, agents_by_id, ordered = _make_windows_and_agents()
    notice = absence_notice_for_round(windows, agents_by_id, ordered, round_number=3, scope="all_inactive")
    assert notice is not None
    assert "Teacher B (on leave)" in notice
    # Teacher C is active in round 3
    assert "Teacher C" not in notice


def test_absence_notice_format_exact_wording() -> None:
    """Format: 'Not present this round: X (reason), Y.' — ends with single period, roster order."""
    windows, agents_by_id, ordered = _make_windows_and_agents()
    # Round 1: only Teacher C absent (no reason)
    notice = absence_notice_for_round(windows, agents_by_id, ordered, round_number=1, scope="all_inactive")
    assert notice == "Not present this round: Teacher C."


def test_absence_notice_departed_only_omits_not_yet_joined() -> None:
    """With departed_only scope, not-yet-joined actors are omitted."""
    windows, agents_by_id, ordered = _make_windows_and_agents()
    # Round 1: Teacher B still active, Teacher C not yet joined
    # departed_only: Teacher B active_until=2 >= 1, so not departed yet → no one departed
    notice_r1 = absence_notice_for_round(windows, agents_by_id, ordered, round_number=1, scope="departed_only")
    assert notice_r1 is None  # no one departed in round 1

    # Round 3: Teacher B has departed (active_until_round=2 < 3), Teacher C active
    notice_r3 = absence_notice_for_round(windows, agents_by_id, ordered, round_number=3, scope="departed_only")
    assert notice_r3 is not None
    assert "Teacher B (on leave)" in notice_r3
    assert "Teacher C" not in notice_r3


def test_absence_notice_none_scope_returns_none() -> None:
    windows, agents_by_id, ordered = _make_windows_and_agents()
    notice = absence_notice_for_round(windows, agents_by_id, ordered, round_number=1, scope="none")
    assert notice is None


def test_absence_notice_all_active_no_notice() -> None:
    """When all agents active, return None."""
    windows = {
        "a": _win("a", frm=1, until=4),
        "b": _win("b", frm=1, until=4),
    }
    agents_by_id = {"a": ("A", "r"), "b": ("B", "r")}
    ordered = ["a", "b"]
    notice = absence_notice_for_round(windows, agents_by_id, ordered, round_number=2, scope="all_inactive")
    assert notice is None


# ---------------------------------------------------------------------------
# §G — resolve_activity_windows validation errors
# ---------------------------------------------------------------------------

def _persona_stub(*, frm: int | None = None, until: int | None = None, reason: str = ""):
    """Minimal PersonaTemplate-like stub."""
    from senna_backend.scenarios.registry import PersonaTemplate

    return PersonaTemplate(
        persona_id="p",
        role="r",
        name="N",
        role_level=1,
        style_cues="",
        beliefs={},
        active_from_round=frm,
        active_until_round=until,
        absence_reason=reason,
    )


def test_resolve_windows_all_defaults_no_windowing() -> None:
    personas = [_persona_stub() for _ in range(3)]
    ids = ["a", "b", "c"]
    wins, warnings = resolve_activity_windows(ids, personas, total_rounds=4)
    assert all(is_active(wins[i], r) for i in ids for r in range(1, 5))
    assert not windowing_active(wins, 4)
    assert warnings == []


def test_resolve_windows_clips_until_gt_total_rounds() -> None:
    personas = [_persona_stub(until=99)]
    wins, warnings = resolve_activity_windows(["a"], personas, total_rounds=4)
    assert wins["a"].active_until_round == 4
    assert any("clipped" in w for w in warnings)


def test_resolve_windows_error_from_gt_total_rounds() -> None:
    # Spec §5: active_from=10 with total_rounds=4 and a blank active_until_round
    # (defaults to R) must report "starts after total_rounds", not from>until.
    personas = [_persona_stub(frm=10)]
    with pytest.raises(ValueError, match="starts after total_rounds=4"):
        resolve_activity_windows(["a"], personas, total_rounds=4)


def test_resolve_windows_error_from_lt_1() -> None:
    personas = [_persona_stub(frm=0)]
    with pytest.raises(ValueError, match="must be >= 1"):
        resolve_activity_windows(["a"], personas, total_rounds=4)


def test_resolve_windows_error_from_gt_until() -> None:
    personas = [_persona_stub(frm=3, until=1)]
    with pytest.raises(ValueError, match="active_from_round > active_until_round"):
        resolve_activity_windows(["a"], personas, total_rounds=4)


def test_resolve_windows_error_zero_active_agents_in_some_round() -> None:
    """slot_a active 1..2, slot_b active 3..4 → rounds 1-4 always have one active agent."""
    personas = [_persona_stub(frm=1, until=2), _persona_stub(frm=3, until=4)]
    wins, _w = resolve_activity_windows(["a", "b"], personas, total_rounds=4)
    # Verify: each round has at least one active agent
    for r in range(1, 5):
        assert any(is_active(wins[x], r) for x in ["a", "b"])

    # Now make a gap: a active 1..1, b active 3..4 → round 2 has no active agent
    personas2 = [_persona_stub(frm=1, until=1), _persona_stub(frm=3, until=4)]
    with pytest.raises(ValueError, match="round 2 has no active agents"):
        resolve_activity_windows(["a", "b"], personas2, total_rounds=4)


def test_resolve_windows_windowing_active_true_when_inactive_round_exists() -> None:
    personas = [_persona_stub(frm=1, until=2), _persona_stub(frm=1, until=4)]
    wins, _ = resolve_activity_windows(["a", "b"], personas, total_rounds=4)
    assert windowing_active(wins, 4) is True


def test_resolve_windows_absence_reason_warning_when_always_active() -> None:
    """absence_reason on an always-active actor → warning, no error."""
    personas = [_persona_stub(reason="some reason")]
    wins, warnings = resolve_activity_windows(["a"], personas, total_rounds=4)
    assert any("absence_reason set but actor is active every round" in w for w in warnings)


# ---------------------------------------------------------------------------
# §G — roster CSV validation
# ---------------------------------------------------------------------------

def test_roster_csv_invalid_active_from_round_raises() -> None:
    from senna_backend.roster.csv_roster import parse_roster_csv
    from senna_backend.scenarios.registry import get_scenario

    sc = get_scenario("psle_reform_mvp")
    csv = "slot,active_from_round\n1,notanumber\n"
    with pytest.raises(ValueError, match="invalid active_from_round"):
        parse_roster_csv(csv, agent_limit=3, scenario=sc)


def test_roster_csv_active_from_round_lt_1_raises() -> None:
    from senna_backend.roster.csv_roster import parse_roster_csv
    from senna_backend.scenarios.registry import get_scenario

    sc = get_scenario("psle_reform_mvp")
    csv = "slot,active_from_round\n1,0\n"
    with pytest.raises(ValueError, match="must be >= 1"):
        parse_roster_csv(csv, agent_limit=3, scenario=sc)


# ---------------------------------------------------------------------------
# §A3 — exclusion_breakdown has no pre_join key when no windows
# ---------------------------------------------------------------------------

def test_exclusion_breakdown_no_pre_join_without_windows() -> None:
    from senna_backend.simulation.memory_context import summarize_memory_context_log

    rows = [
        {"round_number": 1, "observer_agent_id": "a", "candidate_turn_id": "t1",
         "included": False, "exclusion_reason": "recency_cut", "target_scope": "agent",
         "char_truncated": False},
        {"round_number": 1, "observer_agent_id": "a", "candidate_turn_id": "t2",
         "included": True, "exclusion_reason": None, "target_scope": "agent",
         "char_truncated": False},
    ]
    summary = summarize_memory_context_log(rows)
    assert "pre_join" not in summary["exclusion_breakdown"]


def test_exclusion_breakdown_has_pre_join_when_rows_present() -> None:
    from senna_backend.simulation.memory_context import summarize_memory_context_log

    rows = [
        {"round_number": 2, "observer_agent_id": "b", "candidate_turn_id": "t3",
         "included": False, "exclusion_reason": "pre_join", "target_scope": "agent",
         "char_truncated": False},
    ]
    summary = summarize_memory_context_log(rows)
    assert "pre_join" in summary["exclusion_breakdown"]
    assert summary["exclusion_breakdown"]["pre_join"] == 1


# ---------------------------------------------------------------------------
# §A4 — old roster CSV (no window columns) still parses with windows=None
# ---------------------------------------------------------------------------

def test_old_roster_csv_no_window_columns_parses_ok() -> None:
    from senna_backend.roster.csv_roster import parse_roster_csv
    from senna_backend.scenarios.registry import get_scenario

    sc = get_scenario("psle_reform_mvp")
    # CSV without the new activity-window columns
    csv = "slot,persona_id,role,name\n1,principal_001,Principal,Researcher A\n"
    result = parse_roster_csv(csv, agent_limit=3, scenario=sc)
    assert 1 in result.by_slot
    row = result.by_slot[1]
    assert row.active_from_round is None
    assert row.active_until_round is None
    assert row.absence_reason is None
    assert row.window_basis is None


def test_roster_csv_window_columns_parse_correctly() -> None:
    from senna_backend.roster.csv_roster import parse_roster_csv
    from senna_backend.scenarios.registry import get_scenario

    sc = get_scenario("psle_reform_mvp")
    csv = "slot,active_from_round,active_until_round,absence_reason,window_basis\n1,2,4,maternity leave,interview table\n"
    result = parse_roster_csv(csv, agent_limit=5, scenario=sc)
    row = result.by_slot[1]
    assert row.active_from_round == 2
    assert row.active_until_round == 4
    assert row.absence_reason == "maternity leave"
    assert row.window_basis == "interview table"


# ---------------------------------------------------------------------------
# §J1-J4 — tenure draw
# ---------------------------------------------------------------------------

_BANDS_3 = [(1, 4), (5, 10), (11, 16)]  # 3 year bands
_SLOT_IDS = [f"slot_{i:02d}" for i in range(1, 17)]  # 16 slots


def test_tenure_draw_same_draw_id_deterministic() -> None:
    """J1: same draw_id gives identical output."""
    kw = dict(
        slot_ids=_SLOT_IDS,
        tenure_counts={3: 7, 2: 5, 1: 4},
        year_bands=_BANDS_3,
        draw_id="test-draw-2026",
    )
    result_a = draw_tenure_windows(**kw)
    result_b = draw_tenure_windows(**kw)
    assert result_a == result_b


def test_tenure_draw_different_draw_id_gives_different_output() -> None:
    """J1: different draw_id gives different windows for the 16-slot case."""
    base_kw = dict(
        slot_ids=_SLOT_IDS,
        tenure_counts={3: 7, 2: 5, 1: 4},
        year_bands=_BANDS_3,
    )
    result_a = draw_tenure_windows(**base_kw, draw_id="draw-aaa")
    result_b = draw_tenure_windows(**base_kw, draw_id="draw-bbb")
    # With 16 slots and varied tenures, different draw_ids should produce different assignments
    assert result_a != result_b


def test_tenure_draw_counts_match_exactly() -> None:
    """J1: counts per tenure match the input tenure_counts exactly."""
    result = draw_tenure_windows(
        slot_ids=_SLOT_IDS,
        tenure_counts={3: 7, 2: 5, 1: 4},
        year_bands=_BANDS_3,
        draw_id="count-check",
    )
    lengths = {L: 0 for L in [1, 2, 3]}
    for sid, (frm, until) in result.items():
        # Determine tenure from number of bands spanned
        for n_bands in [1, 2, 3]:
            # Find which consecutive bands cover (frm, until)
            for start in range(len(_BANDS_3) - n_bands + 1):
                expected_frm = _BANDS_3[start][0]
                expected_until = _BANDS_3[start + n_bands - 1][1]
                if frm == expected_frm and until == expected_until:
                    lengths[n_bands] += 1
                    break
    assert lengths[3] == 7
    assert lengths[2] == 5
    assert lengths[1] == 4


def test_tenure_draw_pinned_slot_keeps_tenure() -> None:
    """J1: pinned slots keep their tenure."""
    result = draw_tenure_windows(
        slot_ids=_SLOT_IDS,
        tenure_counts={3: 7, 2: 5, 1: 4},
        year_bands=_BANDS_3,
        draw_id="pin-test",
        pinned={"slot_01": 3},
    )
    frm, until = result["slot_01"]
    # Must span 3 consecutive bands
    found = False
    for start in range(len(_BANDS_3) - 3 + 1):
        if frm == _BANDS_3[start][0] and until == _BANDS_3[start + 2][1]:
            found = True
            break
    assert found, f"slot_01 window ({frm}, {until}) doesn't span 3 bands"


def test_tenure_draw_band_boundaries() -> None:
    """J2: windows lie on band boundaries and are consecutive."""
    result = draw_tenure_windows(
        slot_ids=_SLOT_IDS,
        tenure_counts={3: 7, 2: 5, 1: 4},
        year_bands=_BANDS_3,
        draw_id="boundary-test",
    )
    band_starts = {b[0] for b in _BANDS_3}
    band_ends = {b[1] for b in _BANDS_3}
    for sid, (frm, until) in result.items():
        assert frm in band_starts, f"{sid}: {frm} not a band start"
        assert until in band_ends, f"{sid}: {until} not a band end"


def test_tenure_draw_count_mismatch_raises() -> None:
    """J3: sum(tenure_counts) != len(slot_ids) raises."""
    with pytest.raises(ValueError, match="slot count"):
        draw_tenure_windows(
            slot_ids=["a", "b", "c"],
            tenure_counts={1: 2},  # sum=2, len=3 → mismatch
            year_bands=_BANDS_3,
            draw_id="mismatch",
        )


def test_tenure_draw_does_not_disturb_global_random() -> None:
    """J4: draw does not change global random stream."""
    random.seed(1)
    before = random.random()
    random.seed(1)

    draw_tenure_windows(
        slot_ids=_SLOT_IDS,
        tenure_counts={3: 7, 2: 5, 1: 4},
        year_bands=_BANDS_3,
        draw_id="no-global-rng-test",
    )
    after = random.random()
    assert before == after


# ---------------------------------------------------------------------------
# §F3 (pure) — agents_active_both_rounds
# ---------------------------------------------------------------------------

def test_agents_active_both_rounds_basic() -> None:
    windows = {
        "a": _win("a", frm=1, until=4),
        "b": ActivityWindow("b", 1, 2, "", ""),
        "c": ActivityWindow("c", 3, 4, "", ""),
    }

    class FakeAgent:
        def __init__(self, aid: str):
            self.agent_id = aid

    agents = [FakeAgent("a"), FakeAgent("b"), FakeAgent("c")]
    # Round 3: a active in 2 and 3, b inactive in 3 (active until 2), c not active in 2
    result = agents_active_both_rounds(agents, windows, round_number=3)
    ids = {ag.agent_id for ag in result}
    assert "a" in ids
    assert "b" not in ids   # b inactive in round 3
    assert "c" not in ids   # c inactive in round 2 (joins at 3)


def test_agents_active_both_rounds_round1_always_empty() -> None:
    windows = {"a": _win("a", frm=1, until=4)}

    class FakeAgent:
        def __init__(self, aid: str):
            self.agent_id = aid

    result = agents_active_both_rounds([FakeAgent("a")], windows, round_number=1)
    assert result == []


# ---------------------------------------------------------------------------
# §A — filter_turns_min_round pure test
# ---------------------------------------------------------------------------

def test_filter_turns_min_round_removes_prior_rounds() -> None:
    turns = [
        {"round_number": 1, "agent_id": "a", "raw_response": "SENTINEL-r1-aa"},
        {"round_number": 2, "agent_id": "b", "raw_response": "SENTINEL-r2-ab"},
        {"round_number": 3, "agent_id": "a", "raw_response": "SENTINEL-r3-aa"},
    ]
    filtered = filter_turns_min_round(turns, min_round=3)
    assert len(filtered) == 1
    assert filtered[0]["round_number"] == 3


def test_filter_turns_min_round_keeps_all_when_min_1() -> None:
    turns = [{"round_number": r, "agent_id": "a"} for r in range(1, 5)]
    assert filter_turns_min_round(turns, min_round=1) == turns


# ---------------------------------------------------------------------------
# §A — active_agents_per_round_rows
# ---------------------------------------------------------------------------

def test_active_agents_per_round_rows_joined_left() -> None:
    windows = {
        "a": _win("a", frm=1, until=4),
        "b": ActivityWindow("b", 1, 2, "", ""),
        "c": ActivityWindow("c", 3, 4, "", ""),
        "d": _win("d", frm=1, until=4),
    }
    ordered = ["a", "b", "c", "d"]
    rows = active_agents_per_round_rows(windows, ordered, total_rounds=4)
    assert len(rows) == 4

    r1 = rows[0]
    assert r1["round_number"] == 1
    assert set(r1["active_agent_ids"]) == {"a", "b", "d"}
    assert set(r1["inactive_agent_ids"]) == {"c"}
    # joined = agents with active_from_round == round_number; a,b,d all start at round 1
    assert set(r1["joined_agent_ids"]) == {"a", "b", "d"}

    r3 = rows[2]
    assert r3["round_number"] == 3
    assert "c" in r3["joined_agent_ids"]
    assert "b" in r3["left_agent_ids"]
    assert set(r3["active_agent_ids"]) == {"a", "c", "d"}
