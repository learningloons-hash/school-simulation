"""Fidelity tier assignment for sampling strategies (Iteration 22+).

Tier values affect ``config_snapshot.sampling_audit`` and ``AgentInstance.fidelity_tier``.
Execution branches by tier from Iteration 23; ``hybrid_core_remainder`` and synthetic remainders from Iteration 24.
"""

from __future__ import annotations

from mirofish_backend.roster.csv_roster import ParsedRosterRow
from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig
from mirofish_backend.simulation.remainder import is_synthetic_remainder_persona

SAMPLING_STRATEGY_VALUES: frozenset[str] = frozenset(
    {
        "full_census",
        "role_stratified",
        "hybrid_core_remainder",
        "posture_maxvar",
        "network_centrality",
    }
)


def unique_roles_from_scenario(scenario: ScenarioConfig) -> tuple[str, ...]:
    """Distinct ``role`` strings in scenario persona order (first appearance wins)."""
    seen: set[str] = set()
    out: list[str] = []
    for p in scenario.personas:
        if p.role not in seen:
            seen.add(p.role)
            out.append(p.role)
    return tuple(out)


def _role_stratified_for_indices(
    personas: list[PersonaTemplate],
    scenario: ScenarioConfig,
    indices: list[int],
) -> dict[int, tuple[int, str]]:
    """Assign tiers 1/2/3 for the given slot indices (roster-unassigned slots only)."""
    if not indices:
        return {}
    roles_order = unique_roles_from_scenario(scenario)
    roles_in_run = {personas[i].role for i in range(len(personas))}

    out: dict[int, tuple[int, str]] = {}
    tier1_used: set[int] = set()

    for role in roles_order:
        if role not in roles_in_run:
            continue
        for idx in sorted(indices):
            if idx in tier1_used:
                continue
            if personas[idx].role == role:
                out[idx] = (
                    1,
                    f"role_stratified: Tier 1 representative for role {role!r} (first matching slot in run order)",
                )
                tier1_used.add(idx)
                break

    remaining = [i for i in indices if i not in out]
    remaining.sort(key=lambda i: (-personas[i].role_level, i))
    n = len(remaining)
    n_tier3 = n // 2
    for j, idx in enumerate(remaining):
        if j < n_tier3:
            out[idx] = (
                3,
                "role_stratified: Tier 3 among non-representatives (higher role_level cohort)",
            )
        else:
            out[idx] = (
                2,
                "role_stratified: Tier 2 among non-representatives (lower role_level cohort)",
            )
    return out


def _hybrid_core_remainder_for_indices(
    personas: list[PersonaTemplate],
    indices: list[int],
) -> dict[int, tuple[int, str]]:
    """Tier 1 = lowest role_level band; Tier 2 = second band; Tier 3 = rest + synthetic remainders.

    Uses only ``role_level`` (no hardcoded role names). Synthetic personas are always Tier 3.
    """
    if not indices:
        return {}
    out: dict[int, tuple[int, str]] = {}
    core_idx = [i for i in indices if not is_synthetic_remainder_persona(personas[i])]
    for i in indices:
        if is_synthetic_remainder_persona(personas[i]):
            out[i] = (3, "hybrid_core_remainder: synthetic remainder agent (Tier 3)")

    if not core_idx:
        return out

    distinct_levels = sorted({personas[i].role_level for i in core_idx})
    nlv = len(distinct_levels)

    def tier_for_level(lvl: int) -> int:
        if nlv == 1:
            return 1
        if nlv == 2:
            return 1 if lvl == distinct_levels[0] else 2
        # Three or more distinct levels → map to three bands.
        if lvl == distinct_levels[0]:
            return 1
        if lvl == distinct_levels[1]:
            return 2
        return 3

    for idx in core_idx:
        lvl = personas[idx].role_level
        t = tier_for_level(lvl)
        out[idx] = (
            t,
            f"hybrid_core_remainder: role_level {lvl} → Tier {t} (bands={distinct_levels!r})",
        )
    return out


def _any_implementation_posture(personas: list[PersonaTemplate], indices: list[int]) -> bool:
    return any((personas[i].implementation_posture or "").strip() for i in indices)


def _posture_maxvar_for_indices(
    personas: list[PersonaTemplate],
    scenario: ScenarioConfig,
    indices: list[int],
) -> dict[int, tuple[int, str]]:
    """Tier 1 = one agent per distinct non-empty ``implementation_posture``; remainder split by role_level.

    Falls back to ``role_stratified`` when no slot has a posture tag among ``indices``.
    """
    if not indices:
        return {}
    if not _any_implementation_posture(personas, indices):
        partial = _role_stratified_for_indices(personas, scenario, indices)
        return {
            i: (t, f"posture_maxvar (no posture tags; role_stratified): {r}")
            for i, (t, r) in partial.items()
        }

    seen_postures: list[str] = []
    for idx in sorted(indices):
        p = (personas[idx].implementation_posture or "").strip()
        if p and p not in seen_postures:
            seen_postures.append(p)

    out: dict[int, tuple[int, str]] = {}
    tier1_used: set[int] = set()
    for posture in seen_postures:
        for idx in sorted(indices):
            if idx in tier1_used:
                continue
            if (personas[idx].implementation_posture or "").strip() == posture:
                out[idx] = (
                    1,
                    f"posture_maxvar: Tier 1 representative for posture {posture!r}",
                )
                tier1_used.add(idx)
                break

    remaining = [i for i in indices if i not in out]
    remaining.sort(key=lambda i: (-personas[i].role_level, i))
    n = len(remaining)
    n_tier3 = n // 2
    for j, idx in enumerate(remaining):
        if j < n_tier3:
            out[idx] = (
                3,
                "posture_maxvar: Tier 3 among non-representatives (higher role_level cohort)",
            )
        else:
            out[idx] = (
                2,
                "posture_maxvar: Tier 2 among non-representatives (lower role_level cohort)",
            )
    return out


def _network_centrality_for_indices(
    indices: list[int],
    agent_ids_in_order: list[str],
    centrality: dict[str, float],
) -> dict[int, tuple[int, str]]:
    """Tier 1 = all agents tied for maximum degree centrality; remainder split 3/2 like posture_maxvar."""
    if not indices:
        return {}
    scored = [(idx, float(centrality.get(agent_ids_in_order[idx], 0.0))) for idx in indices]
    scored.sort(key=lambda x: (-x[1], x[0]))
    max_c = scored[0][1]
    tier1_idx = {idx for idx, c in scored if c == max_c}
    out: dict[int, tuple[int, str]] = {}
    for idx in tier1_idx:
        c = centrality.get(agent_ids_in_order[idx], 0.0)
        out[idx] = (1, f"network_centrality: Tier 1 (degree centrality {c:.6g} at maximum)")
    remaining = sorted(i for i in indices if i not in out)
    if not remaining:
        return out
    remaining.sort(key=lambda i: (-centrality.get(agent_ids_in_order[i], 0.0), i))
    n = len(remaining)
    n_t3 = n // 2
    for j, idx in enumerate(remaining):
        if j < n_t3:
            out[idx] = (3, "network_centrality: Tier 3 among non-max-centrality agents")
        else:
            out[idx] = (2, "network_centrality: Tier 2 among non-max-centrality agents")
    return out


def compute_fidelity_tiers(
    *,
    sampling_strategy: str,
    scenario: ScenarioConfig,
    personas_for_run: list[PersonaTemplate],
    roster_by_slot: dict[int, ParsedRosterRow] | None,
    agent_ids_in_order: list[str] | None = None,
    network_centrality_by_agent: dict[str, float] | None = None,
) -> tuple[list[int], list[str]]:
    """
    Resolution: roster ``fidelity_tier`` > strategy > default Tier 1.

    Returns parallel lists (tier, rationale) per slot index 0..n-1.
    """
    n = len(personas_for_run)
    tiers = [1] * n
    rationales = [""] * n
    roster = roster_by_slot or {}

    need_strategy: list[int] = []
    for i in range(n):
        row = roster.get(i + 1)
        if row is not None and row.fidelity_tier is not None:
            tiers[i] = row.fidelity_tier
            rationales[i] = "roster_csv fidelity_tier override"
        else:
            need_strategy.append(i)

    strat = (sampling_strategy or "full_census").strip().lower().replace("-", "_")
    if strat == "full_census":
        for i in need_strategy:
            tiers[i] = 1
            rationales[i] = "full_census: all agents Tier 1 (metadata; execution unchanged until Iter 23)"
    elif strat == "role_stratified":
        partial = _role_stratified_for_indices(personas_for_run, scenario, need_strategy)
        for i in need_strategy:
            t, r = partial[i]
            tiers[i] = t
            rationales[i] = r
    elif strat == "hybrid_core_remainder":
        partial = _hybrid_core_remainder_for_indices(personas_for_run, need_strategy)
        for i in need_strategy:
            t, r = partial[i]
            tiers[i] = t
            rationales[i] = r
    elif strat == "posture_maxvar":
        partial = _posture_maxvar_for_indices(personas_for_run, scenario, need_strategy)
        for i in need_strategy:
            t, r = partial[i]
            tiers[i] = t
            rationales[i] = r
    elif strat == "network_centrality":
        if not agent_ids_in_order or len(agent_ids_in_order) != n:
            raise ValueError("network_centrality requires agent_ids_in_order matching personas_for_run length")
        if not network_centrality_by_agent:
            raise ValueError("network_centrality requires network_centrality_by_agent")
        partial = _network_centrality_for_indices(need_strategy, agent_ids_in_order, network_centrality_by_agent)
        for i in need_strategy:
            t, r = partial[i]
            tiers[i] = t
            rationales[i] = r
    else:
        raise ValueError(f"Unknown sampling_strategy {sampling_strategy!r}")

    return tiers, rationales


def build_sampling_audit(
    *,
    sampling_strategy: str,
    tiers: list[int],
    rationales: list[str],
    agent_ids: list[str],
    scenario: ScenarioConfig,
) -> dict:
    """Structured audit for ``config_snapshot.sampling_audit`` (without ``scenario_roles_not_represented``)."""
    roles_order = list(unique_roles_from_scenario(scenario))
    tier_counts: dict[int, int] = {1: 0, 2: 0, 3: 0}
    for t in tiers:
        tier_counts[t] = tier_counts.get(t, 0) + 1

    per_agent = [
        {"agent_id": aid, "tier": t, "rationale": r}
        for aid, t, r in zip(agent_ids, tiers, rationales, strict=True)
    ]
    return {
        "sampling_strategy": sampling_strategy,
        "tier_counts": tier_counts,
        "per_agent": per_agent,
        "scenario_roles_ordered": roles_order,
    }


def build_sampling_audit_extended(
    *,
    sampling_strategy: str,
    tiers: list[int],
    rationales: list[str],
    agent_ids: list[str],
    scenario: ScenarioConfig,
    personas_for_run: list[PersonaTemplate],
) -> dict:
    """Same as ``build_sampling_audit`` plus ``scenario_roles_not_represented``."""
    base = build_sampling_audit(
        sampling_strategy=sampling_strategy,
        tiers=tiers,
        rationales=rationales,
        agent_ids=agent_ids,
        scenario=scenario,
    )
    roles_in_run = {p.role for p in personas_for_run}
    not_rep = [r for r in base["scenario_roles_ordered"] if r not in roles_in_run]
    base["scenario_roles_not_represented"] = not_rep
    enriched: list[dict] = []
    for i, entry in enumerate(base["per_agent"]):
        e = dict(entry)
        if i < len(personas_for_run):
            p = personas_for_run[i]
            e["role"] = p.role
            e["implementation_posture"] = (p.implementation_posture or "").strip() or None
        enriched.append(e)
    base["per_agent"] = enriched
    return base
