"""Named LLM routing policies (Senna Arc 7, iter-33)."""

from __future__ import annotations

from typing import Literal

RoutingPolicy = Literal["local_only", "frontier_only", "hybrid_first_turn"]
LLMProvider = Literal["lmstudio", "anthropic"]

# Sentinel for Tier-3 heuristic turns (not a built-in model profile).
HEURISTIC_PROFILE_SENTINEL = "heuristic"

ROUTING_POLICY_VALUES: frozenset[str] = frozenset(
    {
        "local_only",
        "frontier_only",
        "hybrid_first_turn",
    }
)

# Legacy config_snapshot value kept for backward compatibility.
LEGACY_HYBRID_ROUTING_POLICY = "frontier_first_turn_of_round"


def llm_provider_to_routing_policy(llm_provider: str) -> RoutingPolicy:
    """Map public ``llm_provider`` enum to a routing policy id."""
    m = (llm_provider or "lmstudio").strip().lower()
    if m == "anthropic":
        return "frontier_only"
    if m == "hybrid":
        return "hybrid_first_turn"
    return "local_only"


def routing_policy_from_mode(routing_mode: str) -> RoutingPolicy:
    """Accept legacy ``routing_mode`` (same strings as ``llm_provider``) or policy id."""
    m = (routing_mode or "lmstudio").strip().lower()
    if m in ROUTING_POLICY_VALUES:
        return m  # type: ignore[return-value]
    return llm_provider_to_routing_policy(m)


def resolve_effective_provider(
    *,
    routing_policy: str,
    round_number: int,
    turn_index: int,
) -> LLMProvider:
    """
    Resolve per-turn LLM backend from a named routing policy.

    ``hybrid_first_turn``: frontier on ``turn_index == 1``, local otherwise (unchanged from pre-33 hybrid).
    """
    _ = round_number
    policy = routing_policy_from_mode(routing_policy)
    if policy == "hybrid_first_turn":
        if turn_index == 1:
            return "anthropic"
        return "lmstudio"
    if policy == "frontier_only":
        return "anthropic"
    return "lmstudio"


def resolve_effective_profile_id(
    *,
    routing_policy: str,
    turn_index: int,
    local_profile_id: str,
    frontier_profile_id: str,
) -> str:
    """Profile id used for this turn (audit / export)."""
    policy = routing_policy_from_mode(routing_policy)
    if policy == "frontier_only":
        return frontier_profile_id
    if policy == "hybrid_first_turn":
        return frontier_profile_id if turn_index == 1 else local_profile_id
    return local_profile_id
