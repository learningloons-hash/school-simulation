"""Senna iter-33 — data-driven routing policies."""

import pytest

from mirofish_backend.llm.model_profiles import (
    ANTHROPIC_DEFAULT_ID,
    LOCAL_LMSTUDIO_DEFAULT_ID,
    routing_policy_config_snapshot,
)
from mirofish_backend.llm.routing_policies import (
    LEGACY_HYBRID_ROUTING_POLICY,
    llm_provider_to_routing_policy,
    resolve_effective_profile_id,
    resolve_effective_provider,
    routing_policy_from_mode,
)
from mirofish_backend.llm.router import resolve_effective_provider as router_resolve


@pytest.mark.parametrize(
    ("llm_provider", "expected"),
    [
        ("lmstudio", "local_only"),
        ("anthropic", "frontier_only"),
        ("hybrid", "hybrid_first_turn"),
        ("", "local_only"),
    ],
)
def test_llm_provider_maps_to_routing_policy(llm_provider: str, expected: str) -> None:
    assert llm_provider_to_routing_policy(llm_provider) == expected


def test_hybrid_first_turn_matches_legacy_hybrid_routing_mode() -> None:
    """Per-turn provider resolution unchanged from pre-iter-33 ``routing_mode=hybrid``."""
    for round_number in (1, 3, 9):
        assert (
            resolve_effective_provider(
                routing_policy="hybrid_first_turn",
                round_number=round_number,
                turn_index=1,
            )
            == "anthropic"
        )
        assert (
            resolve_effective_provider(
                routing_policy="hybrid_first_turn",
                round_number=round_number,
                turn_index=2,
            )
            == "lmstudio"
        )
        assert (
            router_resolve(
                routing_mode="hybrid",
                round_number=round_number,
                turn_index=1,
            )
            == "anthropic"
        )
        assert (
            router_resolve(
                routing_mode="hybrid",
                round_number=round_number,
                turn_index=3,
            )
            == "lmstudio"
        )


def test_local_and_frontier_only_policies() -> None:
    assert (
        resolve_effective_provider(
            routing_policy="local_only",
            round_number=1,
            turn_index=1,
        )
        == "lmstudio"
    )
    assert (
        resolve_effective_provider(
            routing_policy="frontier_only",
            round_number=5,
            turn_index=9,
        )
        == "anthropic"
    )


def test_resolve_effective_profile_id_hybrid_first_turn() -> None:
    assert (
        resolve_effective_profile_id(
            routing_policy="hybrid_first_turn",
            turn_index=1,
            local_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            frontier_profile_id=ANTHROPIC_DEFAULT_ID,
        )
        == ANTHROPIC_DEFAULT_ID
    )
    assert (
        resolve_effective_profile_id(
            routing_policy="hybrid_first_turn",
            turn_index=2,
            local_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            frontier_profile_id=ANTHROPIC_DEFAULT_ID,
        )
        == LOCAL_LMSTUDIO_DEFAULT_ID
    )


def test_routing_policy_from_mode_accepts_policy_id() -> None:
    assert routing_policy_from_mode("hybrid_first_turn") == "hybrid_first_turn"


def test_routing_policy_config_snapshot() -> None:
    from mirofish_backend.config import Settings
    from mirofish_backend.llm.model_profiles import resolve_run_profiles

    s = Settings()
    hybrid = resolve_run_profiles(model_profile_id=None, llm_provider="hybrid", settings=s)
    snap = routing_policy_config_snapshot(hybrid)
    assert snap["routing_policy"] == "hybrid_first_turn"
    assert snap["routing_profile_local_id"] == LOCAL_LMSTUDIO_DEFAULT_ID
    assert snap["routing_profile_frontier_id"] == ANTHROPIC_DEFAULT_ID
    assert snap["hybrid_routing_policy"] == LEGACY_HYBRID_ROUTING_POLICY

    local = resolve_run_profiles(model_profile_id=None, llm_provider="lmstudio", settings=s)
    assert routing_policy_config_snapshot(local)["routing_policy"] == "local_only"
    assert routing_policy_config_snapshot(local)["hybrid_routing_policy"] is None
