"""Tier-3 state heuristic (Iteration 24): dampened mean shift from Tier-1/2 + seeded noise."""

from __future__ import annotations

import random
from typing import Any


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def mean_deltas_tier12_for_round(
    round_agents: list[Any],
    states_before: dict[str, tuple[float, float, float]],
    states_after: dict[str, Any],
) -> tuple[float, float, float]:
    """Mean (after - before) for support, resistance, workload over Tier-1/2 agents in ``round_agents``."""
    ds: list[tuple[float, float, float]] = []
    for ag in round_agents:
        if ag.fidelity_tier == 3:
            continue
        aid = ag.agent_id
        b = states_before.get(aid)
        if b is None:
            continue
        af = states_after.get(aid)
        if af is None:
            continue
        b0, b1, b2 = b
        ds.append(
            (
                af.support_level - b0,
                af.resistance_level - b1,
                af.workload_stress - b2,
            )
        )
    if not ds:
        return (0.0, 0.0, 0.0)
    n = len(ds)
    return (
        sum(t[0] for t in ds) / n,
        sum(t[1] for t in ds) / n,
        sum(t[2] for t in ds) / n,
    )


def apply_tier3_heuristic_to_states(
    *,
    tier3_agent_ids: list[str],
    agent_states: dict[str, Any],
    delta_support: float,
    delta_resistance: float,
    delta_workload: float,
    dampening: float,
    noise_std: float,
    rng: random.Random,
) -> None:
    """Mutates ``agent_states`` in place for each Tier-3 agent id."""
    from mirofish_backend.simulation.orchestrator import AgentState

    for aid in tier3_agent_ids:
        st = agent_states.get(aid)
        if st is None:
            continue
        ns = clamp01(
            st.support_level + dampening * delta_support + (rng.gauss(0, noise_std) if noise_std > 0 else 0.0)
        )
        nr = clamp01(
            st.resistance_level
            + dampening * delta_resistance
            + (rng.gauss(0, noise_std) if noise_std > 0 else 0.0)
        )
        nw = clamp01(
            st.workload_stress
            + dampening * delta_workload
            + (rng.gauss(0, noise_std) if noise_std > 0 else 0.0)
        )
        agent_states[aid] = AgentState(
            support_level=ns,
            resistance_level=nr,
            workload_stress=nw,
            belief_posture=st.belief_posture,
        )


def tier3_heuristic_rng(*, random_seed: int, round_number: int) -> random.Random:
    """Deterministic RNG for Tier-3 noise (seeded per round)."""
    mix = (random_seed & 0xFFFFFFFF) ^ (round_number * 0x85EBCA6B) ^ 0xA5A5A5A5
    return random.Random(mix)
