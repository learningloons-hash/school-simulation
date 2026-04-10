# Iteration 25 closeout — Network CSV + `network_centrality` + ADR-002 visibility

**Date:** 2026-04-06 (ship); **post–Iteration 25 hardening** 2026-04-07  
**Theme:** Optional **`network_csv`**; **degree centrality**; **`network_centrality`** sampling strategy; **`round_participants_only`** and **`network_bounded`** visibility policies; **`interaction_visibility`** / **`visibility_effective`** in **`config_snapshot`**.

## Shipped

| Area | Detail |
|------|--------|
| **`simulation/network.py`** | `parse_network_csv` (header `source_agent_id,target_agent_id,influence_weight`); unknown endpoints → **warnings**, row skipped; `degree_centrality`; `undirected_neighbor_map`. |
| **`simulation/sampling_strategy.py`** | **`network_centrality`** in **`SAMPLING_STRATEGY_VALUES`**; `_network_centrality_for_indices` (max-centrality Tier 1; remainder split 2/3). |
| **`simulation/interaction_policy.py`** | **`BROADCAST`** (ADR-002; API **`full`** normalizes to **`broadcast`**), **`ROUND_PARTICIPANTS_ONLY`** (includes **broadcast** turns from any speaker, aligned with **`group_bounded`** / **`network_bounded`**), **`NETWORK_BOUNDED`**; **`visible_turns_for_agent(..., effective_visibility=, network_neighbors=, round_speaker_ids=)`**. |
| **`simulation/orchestrator.py`** | **`network_neighbors`**, **`visibility_effective`**; per-round **`round_speaker_ids`** for visibility. |
| **`api/simulations.py`** | **`network_csv`** on **`SimulationRunRequest`** (max 500k); **`network_centrality`** requires non-empty CSV (Pydantic); **`config_snapshot`**: `network_csv_applied`, `network_edge_count`, **`network_node_count`** (distinct endpoints in parsed edges), **`interaction_policy.interaction_visibility`**, **`visibility_effective`**, **`network_visibility_fallback`**; **`sampling_audit.per_agent[].degree_centrality`**. |
| **`simulation/sampling_report.py`** | **`centrality`**: map `agent_id → degree_centrality` when present. |
| **`api/capabilities.py`** | **`network_csv`** optional meta; **`visibility_policies`** lists ADR-002 values **without** legacy **`full`** (API still accepts **`full`**). |
| **`agent/orchestrator.py`** | **`PlanSimulationParams.network_csv`**; visibility validator (**`full`** normalized to **`broadcast`** for capability checks); **`_simulation_run_request`** forwards **`network_csv`**. |

## Post–Iteration 25 hardening (architect PASS_WITH_ISSUES — 2026-04-07)

Per [`HANDOFF_TO_BUILDER.md` § Post-Iteration 25 hardening](../handoffs/HANDOFF_TO_BUILDER.md#post-iteration-25-hardening-pre-filled--2026-04-07) and [`review-iteration-25.md`](../reviews/review-iteration-25.md):

| Item | Outcome |
|------|---------|
| E2E / integration | **`test_network_queued_run_audit_sampling_report_and_node_count`** — `POST /simulations/run` with **`network_csv`**, **`network_centrality`**, **`network_bounded`**; fake LLM; asserts **`config_snapshot`**, **`sampling_audit`**, **`GET …/sampling-report`**. |
| **`network_node_count`** | Count of unique agent ids appearing as source or target on at least one parsed edge (not **`agent_limit`**). |
| **`GET /capabilities`** | No duplicate **`full`** / **`broadcast`**; planner validation still accepts **`full`** in plans. |
| **`round_participants_only`** | Broadcast turns visible even if speaker ∉ **`round_speaker_ids`**; **`test_round_participants_only_passes_broadcast_from_non_cohort_speaker`**. |
| Docs / minor | **`parse_network_csv`** docstring on duplicate edges; **`SimulationRunRequest.network_csv`** + capabilities text for **`persona_id_NNN`**; test rename **`test_sampling_strategy_values_contains_network_centrality`**. |

## Behaviour notes

- **`network_bounded`** without **`network_csv`**: falls back to **broadcast**, **`run_warnings`** + **`network_visibility_fallback: true`** (ADR-002).
- Default **`build_interaction_policy()`** visibility is **`BROADCAST`** (legacy **`full`** still accepted on **`POST /simulations/run`**).

## Gate evidence

```bash
cd backend && uv run pytest --tb=no -q
# 174 passed, 1 skipped
cd ../frontend && npm run build
```

## Tests

**`tests/test_iteration25.py`** — parse warnings, centrality math, tier assignment, Pydantic guard, capabilities (no legacy **`full`** in list), queued-run E2E. **`test_iteration15_interaction_policy.py`** — **`round_participants_only`** (+ broadcast passthrough), **`network_bounded`**, default **BROADCAST**.

## Next

**Iteration 27** — experiment framework ([`HANDOFF_TO_BUILDER.md`](../handoffs/HANDOFF_TO_BUILDER.md#iteration-27-starter-pre-filled--2026-04-06)).
