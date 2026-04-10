"""Iteration 15: IAD interaction rules and network topology tests."""

from __future__ import annotations

import pytest

from mirofish_backend.simulation.interaction_policy import (
    ChannelType,
    InteractionOverlay,
    InteractionPolicy,
    TurnOrderPolicy,
    VisibilityPolicy,
    apply_turn_order,
    build_interaction_policy,
    channel_for_turn,
    visible_turns_for_agent,
)


# ---------------------------------------------------------------------------
# build_interaction_policy factory
# ---------------------------------------------------------------------------

def test_default_policy_is_iad_neutral() -> None:
    p = build_interaction_policy()
    assert p.turn_order_policy == TurnOrderPolicy.ROUND_ROBIN
    assert p.visibility_policy == VisibilityPolicy.BROADCAST
    assert p.interaction_overlay == InteractionOverlay.NONE


def test_unknown_turn_order_policy_raises() -> None:
    with pytest.raises(ValueError, match="Unknown turn_order_policy"):
        build_interaction_policy(turn_order_policy="spiral")


def test_unknown_visibility_policy_raises() -> None:
    with pytest.raises(ValueError, match="Unknown visibility_policy"):
        build_interaction_policy(visibility_policy="hidden")


def test_unknown_interaction_overlay_raises() -> None:
    with pytest.raises(ValueError, match="Unknown interaction_overlay"):
        build_interaction_policy(interaction_overlay="foo_bar")


def test_school_trinidad_overlay_upgrades_to_hierarchical() -> None:
    """When Trinidad overlay is requested but turn_order is still round_robin, auto-upgrade."""
    p = build_interaction_policy(interaction_overlay="school_trinidad")
    assert p.turn_order_policy == TurnOrderPolicy.HIERARCHICAL
    assert p.interaction_overlay == InteractionOverlay.SCHOOL_TRINIDAD


def test_explicit_round_robin_with_trinidad_still_upgrades() -> None:
    """round_robin + school_trinidad → hierarchical (overlay wins)."""
    p = build_interaction_policy(
        turn_order_policy="round_robin",
        interaction_overlay="school_trinidad",
    )
    assert p.turn_order_policy == TurnOrderPolicy.HIERARCHICAL


def test_explicit_hierarchical_survives() -> None:
    p = build_interaction_policy(turn_order_policy="hierarchical")
    assert p.turn_order_policy == TurnOrderPolicy.HIERARCHICAL


def test_policy_to_dict() -> None:
    p = build_interaction_policy(
        turn_order_policy="hierarchical",
        visibility_policy="group_bounded",
        interaction_overlay="school_trinidad",
    )
    d = p.to_dict()
    assert d["turn_order_policy"] == "hierarchical"
    assert d["visibility_policy"] == "group_bounded"
    assert d["interaction_overlay"] == "school_trinidad"
    assert d["policy_version"] == "1"


# ---------------------------------------------------------------------------
# apply_turn_order
# ---------------------------------------------------------------------------

class _FakePersona:
    def __init__(self, role_level: int) -> None:
        self.role_level = role_level


class _FakeAgent:
    def __init__(self, agent_id: str, role_level: int) -> None:
        self.agent_id = agent_id
        self.persona = _FakePersona(role_level)


def test_round_robin_preserves_order() -> None:
    agents = [_FakeAgent("t1", 3), _FakeAgent("p1", 1), _FakeAgent("m1", 2)]
    policy = build_interaction_policy(turn_order_policy="round_robin")
    result = apply_turn_order(agents, policy)
    assert [a.agent_id for a in result] == ["t1", "p1", "m1"]


def test_hierarchical_sorts_by_role_level() -> None:
    agents = [_FakeAgent("t1", 3), _FakeAgent("p1", 1), _FakeAgent("m1", 2)]
    policy = build_interaction_policy(turn_order_policy="hierarchical")
    result = apply_turn_order(agents, policy)
    assert [a.agent_id for a in result] == ["p1", "m1", "t1"]


def test_hierarchical_is_stable_within_tier() -> None:
    agents = [_FakeAgent("t1", 3), _FakeAgent("t2", 3), _FakeAgent("p1", 1)]
    policy = build_interaction_policy(turn_order_policy="hierarchical")
    result = apply_turn_order(agents, policy)
    # principal first, then teachers in original order
    assert result[0].agent_id == "p1"
    assert [a.agent_id for a in result[1:]] == ["t1", "t2"]


# ---------------------------------------------------------------------------
# visible_turns_for_agent
# ---------------------------------------------------------------------------

class _FakeContext:
    def __init__(self, group_ids: tuple[str, ...]) -> None:
        self.group_ids = group_ids


class _FakeAgentWithGroups:
    def __init__(self, agent_id: str, group_ids: tuple[str, ...]) -> None:
        self.agent_id = agent_id
        self.context = _FakeContext(group_ids)


def _turn(agent_id: str, interaction_type: str, group_ids: list[str] | None = None) -> dict:
    return {"agent_id": agent_id, "interaction_type": interaction_type, "group_ids": group_ids}


def test_full_visibility_returns_all_turns() -> None:
    agent = _FakeAgentWithGroups("a1", ("g1",))
    turns = [
        _turn("a2", "broadcast"),
        _turn("a3", "reply", ["g2"]),
    ]
    policy = build_interaction_policy(visibility_policy="full")
    assert visible_turns_for_agent(turns, agent, policy) == turns


def test_group_bounded_broadcasts_always_visible() -> None:
    agent = _FakeAgentWithGroups("a1", ("g1",))
    turns = [
        _turn("a2", "broadcast"),
        _turn("a3", "reply", ["g2"]),  # no shared group
    ]
    policy = build_interaction_policy(visibility_policy="group_bounded")
    result = visible_turns_for_agent(turns, agent, policy)
    assert len(result) == 1
    assert result[0]["interaction_type"] == "broadcast"


def test_group_bounded_shared_group_visible() -> None:
    agent = _FakeAgentWithGroups("a1", ("g1", "g2"))
    turns = [
        _turn("a2", "reply", ["g2"]),   # shares g2
        _turn("a3", "reply", ["g3"]),   # no shared group
    ]
    policy = build_interaction_policy(visibility_policy="group_bounded")
    result = visible_turns_for_agent(turns, agent, policy)
    assert len(result) == 1
    assert result[0]["agent_id"] == "a2"


def test_group_bounded_own_turns_always_visible() -> None:
    agent = _FakeAgentWithGroups("a1", ("g1",))
    turns = [_turn("a1", "reply", ["g999"])]  # own turn, different group
    policy = build_interaction_policy(visibility_policy="group_bounded")
    result = visible_turns_for_agent(turns, agent, policy)
    assert len(result) == 1


def test_group_bounded_agent_without_groups_falls_back_to_full() -> None:
    agent = _FakeAgentWithGroups("a1", ())
    turns = [_turn("a2", "reply", ["g1"]), _turn("a3", "reply", [])]
    policy = build_interaction_policy(visibility_policy="group_bounded")
    result = visible_turns_for_agent(turns, agent, policy)
    assert result == turns


def test_round_participants_only_filters_to_cohort() -> None:
    agent = _FakeAgentWithGroups("a1", ("g1",))
    turns = [
        _turn("a1", "broadcast"),
        _turn("a2", "direct"),
        _turn("a3", "direct"),
    ]
    policy = build_interaction_policy(visibility_policy="round_participants_only")
    spk = frozenset({"a1", "a2"})
    result = visible_turns_for_agent(turns, agent, policy, round_speaker_ids=spk)
    assert {t["agent_id"] for t in result} == {"a1", "a2"}


def test_round_participants_only_passes_broadcast_from_non_cohort_speaker() -> None:
    """Broadcast turns are visible even when the speaker is not in round_speaker_ids (ADR-002 alignment)."""
    agent = _FakeAgentWithGroups("a1", ("g1",))
    turns = [
        _turn("a1", "direct"),
        _turn("a2", "broadcast"),
        _turn("a3", "direct"),
    ]
    policy = build_interaction_policy(visibility_policy="round_participants_only")
    spk = frozenset({"a1", "a3"})
    result = visible_turns_for_agent(turns, agent, policy, round_speaker_ids=spk)
    assert {t["agent_id"] for t in result} == {"a1", "a2", "a3"}


def test_network_bounded_neighbors_and_broadcast() -> None:
    agent = _FakeAgentWithGroups("a1", ())
    turns = [
        _turn("a1", "direct"),
        _turn("a2", "broadcast"),
        _turn("a3", "direct"),
        _turn("a4", "direct"),
    ]
    policy = build_interaction_policy(visibility_policy="network_bounded")
    nbr = {"a1": frozenset({"a3"})}
    result = visible_turns_for_agent(
        turns, agent, policy, network_neighbors=nbr, effective_visibility=VisibilityPolicy.NETWORK_BOUNDED
    )
    ids = {t["agent_id"] for t in result}
    assert ids == {"a1", "a2", "a3"}  # own + broadcast + neighbor a3


# ---------------------------------------------------------------------------
# channel_for_turn
# ---------------------------------------------------------------------------

def test_iad_neutral_first_turn_is_broadcast() -> None:
    policy = build_interaction_policy()
    c = channel_for_turn(turn_index=1, total_speakers=5, agent_role_level=3, policy=policy)
    assert c == ChannelType.BROADCAST


def test_iad_neutral_last_turn_is_meeting() -> None:
    policy = build_interaction_policy()
    c = channel_for_turn(turn_index=5, total_speakers=5, agent_role_level=3, policy=policy)
    assert c == ChannelType.MEETING


def test_iad_neutral_middle_turn_is_direct() -> None:
    policy = build_interaction_policy()
    c = channel_for_turn(turn_index=3, total_speakers=5, agent_role_level=3, policy=policy)
    assert c == ChannelType.DIRECT


def test_trinidad_overlay_principal_always_broadcast() -> None:
    policy = build_interaction_policy(interaction_overlay="school_trinidad")
    # Even if turn_index is 3 (middle), principal role_level=1 → broadcast
    c = channel_for_turn(turn_index=3, total_speakers=5, agent_role_level=1, policy=policy)
    assert c == ChannelType.BROADCAST


def test_trinidad_overlay_hod_last_turn_is_meeting() -> None:
    policy = build_interaction_policy(interaction_overlay="school_trinidad")
    c = channel_for_turn(turn_index=5, total_speakers=5, agent_role_level=2, policy=policy)
    assert c == ChannelType.MEETING


def test_trinidad_overlay_hod_middle_turn_is_direct() -> None:
    policy = build_interaction_policy(interaction_overlay="school_trinidad")
    c = channel_for_turn(turn_index=3, total_speakers=5, agent_role_level=2, policy=policy)
    assert c == ChannelType.DIRECT


# ---------------------------------------------------------------------------
# Scenario registry reads interaction_overlay
# ---------------------------------------------------------------------------

def test_scenario_registry_defaults_interaction_overlay_to_none() -> None:
    from mirofish_backend.scenarios.registry import get_scenario
    cfg = get_scenario("psle_reform_mvp")
    assert cfg.interaction_overlay == "none"


def test_scenario_from_mapping_reads_interaction_overlay() -> None:
    from mirofish_backend.scenarios.registry import scenario_from_mapping
    cfg = scenario_from_mapping({
        "scenario_id": "test_overlay",
        "name": "Test overlay",
        "policy_events": {"1": "Event one"},
        "personas": [
            {
                "persona_id": "p1",
                "role": "principal",
                "name": "Principal",
                "role_level": 1,
                "style_cues": "",
                "beliefs": {},
            }
        ],
        "interaction_overlay": "school_trinidad",
    })
    assert cfg.interaction_overlay == "school_trinidad"


# ---------------------------------------------------------------------------
# SimulationRunRequest exposes new fields (API contract)
# ---------------------------------------------------------------------------

def test_simulation_run_request_defaults(monkeypatch, tmp_path) -> None:
    from fastapi.testclient import TestClient
    from mirofish_backend.main import app
    db = tmp_path / "iter15_test.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as client:
        # Just validate the request is accepted with new default fields
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 1,
                "agent_limit": 1,
                "random_seed": 7,
                "turn_order_policy": "round_robin",
                "visibility_policy": "full",
                "interaction_overlay": "none",
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "id" in body


def test_simulation_run_request_hierarchical_accepted(monkeypatch, tmp_path) -> None:
    from fastapi.testclient import TestClient
    from mirofish_backend.main import app
    db = tmp_path / "iter15_test2.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 1,
                "agent_limit": 1,
                "random_seed": 9,
                "turn_order_policy": "hierarchical",
                "visibility_policy": "group_bounded",
                "interaction_overlay": "school_trinidad",
            },
        )
    assert r.status_code == 200, r.text
