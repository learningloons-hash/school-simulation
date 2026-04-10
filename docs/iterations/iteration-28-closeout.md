# Iteration 28 closeout — Convergence stopping criterion

**Date:** 2026-04-07 (ship); **post–28 hardening** 2026-04-08  
**Theme:** Optional **population-level** convergence stop: mean absolute change across agents’ `support_level`, `resistance_level`, and `workload_stress` vs the prior round; **`convergence_patience`** consecutive rounds below **`convergence_threshold`** ends the run early.

## Shipped

| Area | Detail |
|------|--------|
| **API** | `SimulationRunRequest`: optional **`convergence_threshold`** (0–1, omit = disabled); **`convergence_patience`** (1–25, default 2). |
| **`GET /simulations/{id}`** | **`converged_at_round`**; **`state_timeline[].global_state.convergence_delta`** (round ≥ 2 only). |
| **DB** | **`global_state_snapshots.convergence_delta`** (nullable); **`simulation_runs.converged_at_round`** (nullable). |
| **`config_snapshot`** | **`convergence_threshold`**, **`convergence_patience`**, **`converged_at_round`** (updated on early stop). |
| **Export** | **`export_version` `7`**; run metadata **`converged_at_round`**; **`global_state_snapshots`** / CSV include **`convergence_delta`** when present. |
| **`GET /capabilities`** | **`simulation_run`** + **`experiments`** text notes convergence fields. |
| **Frontend** | Run tab: optional threshold + patience; Live tab: **convergence δ** sparkline (rounds 2+), **Converged at round N** banner. |

## Post–Iteration 28 hardening (2026-04-08)

Architect **PASS_WITH_ISSUES** follow-ups from [`review-iteration-28.md`](../reviews/review-iteration-28.md):

| Item | Change |
|------|--------|
| **Experiments** | **`ExperimentCreateRequest`**: **`convergence_threshold`**, **`convergence_patience`** (shared across child runs); merged via **`_merge_to_simulation_request`**. |
| **Agent orchestrator** | **`PlanSimulationParams`** + **`_simulation_run_request`**; **`validate_plan_against_capabilities`** range checks; planner template includes optional fields. |
| **Streak reset** | **`test_convergence_streak_resets_then_requires_fresh_patience`** — varying fake LLM, stop at round **6** with patience **2**. |
| **Experiment E2E** | **`test_experiment_create_passes_convergence_to_child_runs`** — both strategies converge; comparison includes **`convergence_delta`**. |
| **Comparison / CSV** | **`get_merged_round_metrics`** selects **`convergence_delta`**; experiment **`comparison`** + **`comparison.csv`** column. |
| **Poll helper** | **`get_simulation_run_status_only`** includes **`converged_at_round`** for experiment detail run rows. |
| **Experiments UI** | Optional convergence on create; per-run **Converged R*n*** vs **Full *n* rounds**; sparkline metric **`convergence_delta`**; details table **cd** column. |
| **Defensive** | **`_population_convergence_delta`** skips agents missing from **`prev`**. |

## Behaviour notes

- Round **1** has no prior snapshot → **`convergence_delta`** is omitted / null; streak is not advanced from round 1.
- Tier-3 agents participate in the population mean (same as architect spec).
- **`belief_posture`** is excluded from the metric (non-numeric).
- Early completion sets **`status=completed`**, **`current_round` = last finished round**, and **`converged_at_round`** on the row and in **`config_snapshot`**.

## Known limitation

Large Tier-3 cohorts with damped heuristic motion may yield small deltas and earlier stops; noted for thesis interpretation.

## Gate evidence

```bash
cd backend && uv run pytest --tb=no -q
# 186 passed, 1 skipped
cd ../frontend && npm run build
```

## Tests

**`tests/test_iteration28.py`** — early stop; full rounds; export JSON; streak reset; experiment + convergence; agent plan validation (+ out-of-range threshold via **`model_construct`**).

## Next

**Iteration 29** — run economics (tokens + estimated cost) per [`HANDOFF_TO_BUILDER.md`](../handoffs/HANDOFF_TO_BUILDER.md) § **Iteration 29 starter**. Prerequisite: **28 + post–28 hardening** complete.
