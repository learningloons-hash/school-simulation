"""
Interaction policy objects for the MiroFish simulation engine.

Iteration 15 — IAD Interaction Rules + Network Topology
========================================================

This module encodes the theoretical framework (IAD-shaped rules, Trinidad overlay)
as named policy objects that control:

  1. **Channel types** — what kind of message each turn represents
     (broadcast, direct, meeting) as named enums, not ad-hoc strings.

  2. **Turn order policy** — the sequence in which agents speak each round.
     Named modes: ``round_robin`` (previous default) and ``hierarchical``
     (ascending ``role_level`` order: lowest number first, i.e. highest authority speaks first).

  3. **Visibility graph** — which agents receive which turns in their
     context window. Currently: ``full`` (everyone sees everything, previous
     default) or ``group_bounded`` (agents only see turns from their own
     groups plus any broadcast).

  4. **Domain overlays** — optional scenario flags attach domain-specific defaults.
     ``interaction_overlay: "school_trinidad"`` is a **plug-in** for Trinidad-style
     school hierarchy (channel mix, hierarchical turn cues). Other domains can add
     their own overlay values following the same pattern (e.g. ``corporate_hierarchy``,
     ``public_forum``) without changing core engine code. When overlay is ``none``,
     IAD-neutral defaults apply.

ADR-002 documents these as a versioned contract (same discipline as
AgentContextV1 in ADR-001).

Usage::

    from mirofish_backend.simulation.interaction_policy import (
        build_interaction_policy,
        apply_turn_order,
        visible_turns_for_agent,
        ChannelType,
    )

    policy = build_interaction_policy(
        turn_order_policy="hierarchical",
        visibility_policy="group_bounded",
        interaction_overlay="school_trinidad",
    )
    ordered_agents = apply_turn_order(agents, policy)
    visible = visible_turns_for_agent(recent_turns, agent, policy)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass

INTERACTION_POLICY_VERSION = "1"

# ---------------------------------------------------------------------------
# Channel types
# ---------------------------------------------------------------------------

class ChannelType(str, enum.Enum):
    """Named channel types — replaces ad-hoc string literals in the orchestrator."""
    BROADCAST = "broadcast"    # All agents in the simulation hear this turn
    DIRECT = "direct"          # One-to-one, only target agent sees it in context
    MEETING = "meeting"        # Group-bounded; all members of the speaker's group(s) hear it


# ---------------------------------------------------------------------------
# Turn order policies
# ---------------------------------------------------------------------------

class TurnOrderPolicy(str, enum.Enum):
    ROUND_ROBIN = "round_robin"
    """Sequential order as originally seeded — all agents take one turn per round."""

    HIERARCHICAL = "hierarchical"
    """
    Authority order: agents with lower ``role_level`` speak first (1 = highest authority).
    Typical school packs use 1/2/3 for leadership / middle / frontline; any domain may
    assign integers the same way. Pair with a domain overlay (e.g. ``school_trinidad``)
    for channel defaults; the sort key remains generic ``role_level``.
    Within each tier, the original seeding order is preserved.
    """


# ---------------------------------------------------------------------------
# Visibility policies
# ---------------------------------------------------------------------------

class VisibilityPolicy(str, enum.Enum):
    BROADCAST = "broadcast"
    """ADR-002 / full-information: every agent sees every turn in the window (API alias ``full``)."""

    FULL = "full"
    """Legacy alias for ``broadcast`` — normalized in :func:`build_interaction_policy`."""

    GROUP_BOUNDED = "group_bounded"
    """
    Each agent sees:
    - All BROADCAST turns (school-wide).
    - Turns from agents that share at least one group_id with the observer.
    - The observer's own prior turns.
    Agents with no groups fall back to FULL visibility.
    """

    ROUND_PARTICIPANTS_ONLY = "round_participants_only"
    """
    ADR-002: each agent sees only turns spoken by agents selected for the current round
    (plus own prior turns). Pair with ``sample_k_per_round`` for partial cohorts.
    """

    NETWORK_BOUNDED = "network_bounded"
    """
    ADR-002: see turns from neighbors in the run's influence network CSV (plus broadcast
    turns and own turns). Without a network graph the orchestrator falls back to broadcast
    and records a warning.
    """


# ---------------------------------------------------------------------------
# Interaction overlay
# ---------------------------------------------------------------------------

class InteractionOverlay(str, enum.Enum):
    NONE = "none"
    SCHOOL_TRINIDAD = "school_trinidad"
    """
    Activates school-specific channel defaults from Trinidad's (2001) model:
    - Turn order: hierarchical
    - Channel: broadcast for principal, direct/meeting for HoDs→teachers
    - Meeting channel for group_bounded visibility
    """


# ---------------------------------------------------------------------------
# Policy object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InteractionPolicy:
    """
    Immutable policy snapshot for a single simulation run.
    All fields are versioned via ``policy_version``.
    """
    turn_order_policy: TurnOrderPolicy = TurnOrderPolicy.ROUND_ROBIN
    visibility_policy: VisibilityPolicy = VisibilityPolicy.BROADCAST
    interaction_overlay: InteractionOverlay = InteractionOverlay.NONE
    policy_version: str = INTERACTION_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_order_policy": self.turn_order_policy.value,
            "visibility_policy": self.visibility_policy.value,
            "interaction_overlay": self.interaction_overlay.value,
            "policy_version": self.policy_version,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_interaction_policy(
    *,
    turn_order_policy: str = "round_robin",
    visibility_policy: str = "broadcast",
    interaction_overlay: str = "none",
) -> InteractionPolicy:
    """
    Construct an :class:`InteractionPolicy` from string parameters.
    Validates values; raises ``ValueError`` on unknown strings.

    Args:
        turn_order_policy: ``"round_robin"`` or ``"hierarchical"``
        visibility_policy: ``"full"`` or ``"broadcast"`` | ``"group_bounded"`` |
        ``"round_participants_only"`` | ``"network_bounded"``
        interaction_overlay: ``"none"`` or ``"school_trinidad"``

    When ``interaction_overlay == "school_trinidad"`` and the caller has not
    explicitly set ``turn_order_policy``, the overlay upgrades the default to
    ``hierarchical``.
    """
    try:
        top = TurnOrderPolicy(turn_order_policy.strip().lower())
    except ValueError as e:
        valid = [v.value for v in TurnOrderPolicy]
        raise ValueError(f"Unknown turn_order_policy {turn_order_policy!r}; valid: {valid}") from e

    vis_raw = visibility_policy.strip().lower()
    if vis_raw == "full":
        vis_raw = "broadcast"
    try:
        vis = VisibilityPolicy(vis_raw)
    except ValueError as e:
        valid = sorted({v.value for v in VisibilityPolicy})
        raise ValueError(f"Unknown visibility_policy {visibility_policy!r}; valid: {valid}") from e

    try:
        overlay = InteractionOverlay(interaction_overlay.strip().lower())
    except ValueError as e:
        valid = [v.value for v in InteractionOverlay]
        raise ValueError(f"Unknown interaction_overlay {interaction_overlay!r}; valid: {valid}") from e

    # Overlay upgrades: school_trinidad implies hierarchical order by default
    if overlay == InteractionOverlay.SCHOOL_TRINIDAD and turn_order_policy == "round_robin":
        top = TurnOrderPolicy.HIERARCHICAL

    return InteractionPolicy(
        turn_order_policy=top,
        visibility_policy=vis,
        interaction_overlay=overlay,
    )


# ---------------------------------------------------------------------------
# Turn order
# ---------------------------------------------------------------------------

def apply_turn_order(
    agents: list[Any],
    policy: InteractionPolicy,
) -> list[Any]:
    """
    Re-order a list of :class:`~mirofish_backend.simulation.orchestrator.AgentInstance`
    objects according to the policy.

    Returns a **new** list; the input is not mutated.

    For ``ROUND_ROBIN`` the original order is preserved.
    For ``HIERARCHICAL`` agents are sorted by ``role_level`` (ascending),
    preserving original intra-tier order (stable sort).
    """
    if policy.turn_order_policy == TurnOrderPolicy.HIERARCHICAL:
        return sorted(agents, key=lambda a: getattr(a.persona, "role_level", 99))
    return list(agents)


# ---------------------------------------------------------------------------
# Visibility filtering
# ---------------------------------------------------------------------------

def visible_turns_for_agent(
    recent_turns: list[dict[str, Any]],
    agent: Any,
    policy: InteractionPolicy,
    *,
    effective_visibility: VisibilityPolicy | None = None,
    network_neighbors: dict[str, frozenset[str]] | None = None,
    round_speaker_ids: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Filter ``recent_turns`` (from :func:`~mirofish_backend.db.repo.get_recent_interactions`)
    to only those visible to ``agent`` under the given policy.

    ``effective_visibility`` overrides ``policy.visibility_policy`` when the orchestrator
    applies ADR-002 fallbacks (e.g. ``network_bounded`` without a graph → broadcast).

    For ``BROADCAST`` / legacy ``FULL``: return all turns unchanged.

    For ``GROUP_BOUNDED`` visibility:
    - Turns with ``interaction_type == "broadcast"`` are always visible.
    - Turns whose ``group_ids`` share at least one group with the observer are visible.
    - The observer's own turns are always visible.
    - Agents with no group_ids fall back to FULL (they hear everything).

    For ``ROUND_PARTICIPANTS_ONLY``: own turns; turns whose ``agent_id`` is in
    ``round_speaker_ids`` (current-round speaking cohort); and turns with
    ``interaction_type == "broadcast"`` (same as ``GROUP_BOUNDED`` / ``NETWORK_BOUNDED``).

    For ``NETWORK_BOUNDED``: own turns, all broadcast turns, and turns whose speaker is
    in ``network_neighbors[observer_id]``. If ``network_neighbors`` is None or empty
    for the observer, caller should pass ``effective_visibility=BROADCAST`` instead.
    """
    vis = effective_visibility if effective_visibility is not None else policy.visibility_policy
    if vis in (VisibilityPolicy.FULL, VisibilityPolicy.BROADCAST):
        return recent_turns

    observer_id: str = agent.agent_id

    if vis == VisibilityPolicy.ROUND_PARTICIPANTS_ONLY:
        spk = round_speaker_ids or frozenset()
        out_rp: list[dict[str, Any]] = []
        for turn in recent_turns:
            tid = turn.get("agent_id")
            if tid == observer_id:
                out_rp.append(turn)
                continue
            if turn.get("interaction_type") == ChannelType.BROADCAST.value:
                out_rp.append(turn)
                continue
            if tid in spk:
                out_rp.append(turn)
        return out_rp

    if vis == VisibilityPolicy.NETWORK_BOUNDED:
        nbrs = (network_neighbors or {}).get(observer_id, frozenset())
        out_nb: list[dict[str, Any]] = []
        for turn in recent_turns:
            tid = turn.get("agent_id")
            if tid == observer_id:
                out_nb.append(turn)
                continue
            if turn.get("interaction_type") == ChannelType.BROADCAST.value:
                out_nb.append(turn)
                continue
            if tid in nbrs:
                out_nb.append(turn)
        return out_nb

    # GROUP_BOUNDED
    observer_groups: frozenset[str] = frozenset(getattr(agent.context, "group_ids", ()) or ())

    # Fallback to full if observer has no groups
    if not observer_groups:
        return recent_turns

    visible: list[dict[str, Any]] = []
    for turn in recent_turns:
        if turn.get("agent_id") == observer_id:
            visible.append(turn)
            continue
        if turn.get("interaction_type") == ChannelType.BROADCAST.value:
            visible.append(turn)
            continue
        turn_groups: frozenset[str] = frozenset(turn.get("group_ids") or [])
        if turn_groups & observer_groups:
            visible.append(turn)

    return visible


# ---------------------------------------------------------------------------
# Channel selection helper
# ---------------------------------------------------------------------------

def channel_for_turn(
    turn_index: int,
    total_speakers: int,
    agent_role_level: int,
    policy: InteractionPolicy,
) -> ChannelType:
    """
    Decide which :class:`ChannelType` a given turn should use.

    Default (IAD-neutral) rules:
    - First turn → BROADCAST
    - Last turn → MEETING
    - Middle turns → DIRECT (reply)

    Trinidad overlay refinements:
    - Principal (role_level == 1) always uses BROADCAST.
    - HoDs (role_level == 2) use DIRECT for reply turns, MEETING for summary.
    - Teachers (role_level == 3) use DIRECT.
    """
    if policy.interaction_overlay == InteractionOverlay.SCHOOL_TRINIDAD:
        if agent_role_level == 1:
            return ChannelType.BROADCAST
        if turn_index == total_speakers:
            return ChannelType.MEETING
        return ChannelType.DIRECT

    # IAD-neutral defaults
    if turn_index == 1:
        return ChannelType.BROADCAST
    if turn_index == total_speakers:
        return ChannelType.MEETING
    return ChannelType.DIRECT
