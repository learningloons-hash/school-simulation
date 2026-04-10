# Iteration 22 closeout — Sampling strategy contract (metadata only)

**Date:** 2026-04-06  
**Status:** Shipped — **Architect PASS**; pre–Iteration 23 test gaps from review **closed** in repo.  
**Theme:** Formal `sampling_strategy` and auditable fidelity tiers on runs; roster override; capabilities + agent planner wiring. **No** change to LLM execution (all agents full tier until Iteration 23).

## Shipped

| Item | Detail |
|------|--------|
| **`simulation/sampling_strategy.py`** | `SAMPLING_STRATEGY_VALUES` (`full_census` \| `role_stratified`); `unique_roles_from_scenario`; `compute_fidelity_tiers` (roster `fidelity_tier` overrides strategy); `build_sampling_audit` / `build_sampling_audit_extended` (adds `scenario_roles_not_represented` when the run omits some scenario roles). |
| **`api/simulations.py`** | `SimulationRunRequest.sampling_strategy` (validated); personas from roster or scenario; tier list + audit; `config_snapshot` gains `sampling_strategy` and `sampling_audit`. |
| **`roster/csv_roster.py`** | Optional column `fidelity_tier` (1–3); `ParsedRosterRow.fidelity_tier`. |
| **`simulation/orchestrator.py`** | `AgentInstance.fidelity_tier`; `_build_agent_instances` / `run_simulation_task` accept `fidelity_tiers`. |
| **`api/capabilities.py`** | `sampling_strategies`, `fidelity_tiers` under `simulation_run`. |
| **`agent/orchestrator.py`** | `PlanSimulationParams.sampling_strategy`; validation vs capabilities; planner JSON + `_simulation_run_request` forward field. |
| **Roster template** | `ROSTER_CSV_TEMPLATE` documents `fidelity_tier`. |

## Pre–Iteration 23 fixes (architect review — same gate)

| Item | Detail |
|------|--------|
| **`test_role_stratified_all_same_role`** | Four agents, same role (`teacher`); `role_stratified` → one Tier 1 representative, remainder in tiers 2/3; rationales present. |
| **`test_sampling_audit_reports_missing_roles`** | Principal-only personas; `build_sampling_audit_extended` → `middle_manager` and `teacher` in `scenario_roles_not_represented`, not `principal`. |

Documented in **`HANDOFF_TO_BUILDER.md`** § *Pre-Iteration 23 fixes* (marked applied).

## Out of scope (as specified)

- Tier-aware prompts or reduced LLM usage — **Iteration 23**.

## Gate evidence

```bash
cd backend && pytest --tb=short -q
# 146 passed, 1 skipped
cd ../frontend && npm run build
```

## New tests (`tests/test_iteration22.py`)

| Test | What it verifies |
|------|-----------------|
| `test_unique_roles_from_scenario_order` | PSLE scenario role order |
| `test_full_census_all_tier_one` | All agents tier 1 + rationale |
| `test_role_stratified_three_distinct_roles_all_tier_one` | One agent per distinct role → all tier 1 |
| `test_role_stratified_all_same_role` | Degenerate same-role cohort → one Tier 1, rest 2/3 (pre–Iter 23) |
| `test_sampling_audit_reports_missing_roles` | `scenario_roles_not_represented` in extended audit (pre–Iter 23) |
| `test_role_stratified_duplicate_roles_splits_remainder` | Extra same-role slots → tiers 2/3 by `role_level` order |
| `test_roster_fidelity_tier_overrides_strategy` | Roster column beats `role_stratified` |
| `test_roster_invalid_fidelity_tier_raises` | CSV validation |
| `test_api_sampling_strategy_invalid_422` | Bad strategy → 422 |
| `test_api_config_snapshot_sampling_audit_full_census` | `config_snapshot` + audit shape (tier_counts keys normalized after JSON round-trip) |
| `test_capabilities_includes_sampling_strategies` | `/capabilities` |
| `test_build_agent_instances_receives_fidelity_tiers` | `AgentInstance.fidelity_tier` wiring |

## Note for consumers

`tier_counts` in persisted `config_snapshot` may use **string** keys (`"1"`, `"2"`, `"3"`) after JSON/SQLite round-trip; tests normalize with `int(k)` when asserting.

## Next

**Iteration 23** — tier-aware orchestrator: simplified Tier-2 prompts, Tier-3 heuristic placeholder (no LLM), `fidelity_tier` on turns + export — see **`HANDOFF_TO_BUILDER.md`** Iteration 23 starter.
