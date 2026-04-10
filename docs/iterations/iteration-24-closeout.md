# Iteration 24 closeout — Tier-3 heuristic + hybrid_core_remainder + scale 300

**Date:** 2026-04-06  
**Status:** Shipped — pending **Architect PASS**.  
**Theme:** Post-round Tier-3 state updates from mean Tier-1/2 deltas (+ seeded noise); **`hybrid_core_remainder`** sampling; synthetic **`synthetic_remainder_*`** personas from Gaussian initial state; **`remainder_config`** on **`POST /simulations/run`**; **`agent_limit` / `speakers_per_round` / `aggregation_threshold` max 300**.

## Shipped

| Area | Detail |
|------|--------|
| **`simulation/heuristic.py`** | `mean_deltas_tier12_for_round`, `apply_tier3_heuristic_to_states`, `tier3_heuristic_rng`. |
| **`simulation/remainder.py`** | `build_synthetic_remainder_personas`, `is_synthetic_remainder_persona` (`synthetic_remainder_` prefix). |
| **`simulation/sampling_strategy.py`** | **`hybrid_core_remainder`** in **`SAMPLING_STRATEGY_VALUES`**; `_hybrid_core_remainder_for_indices` (role_level bands; synthetics forced Tier 3). |
| **`simulation/orchestrator.py`** | After each round’s `gather`: if any Tier-1/2 spoke, apply heuristic to **all** Tier-3 agents in the roster; skip when the round has **no** Tier-1/2 speakers (Tier-3-only runs stable). Params **`tier_3_dampening`**, **`tier_3_noise_std`**. |
| **`api/simulations.py`** | **`GaussianDistParams`**, **`RemainderConfigParams`**, **`remainder_config`** on **`SimulationRunRequest`**; **`core_limit`** population draw + roster build; append synthetics; **`config_snapshot`**: `remainder_config`, `synthetic_remainder_count`, `core_agent_limit`, `tier_3_heuristic`. |
| **`api/capabilities.py`** | `agent_limit` / `speakers_per_round` / `aggregation_threshold` **max 300**; **`remainder_config`** blurb; **`sampling_strategies`** includes **`hybrid_core_remainder`**. |
| **`agent/orchestrator.py`** | **`PlanSimulationParams.remainder_config`**; planner JSON **`remainder_config`**; validation vs **`agent_limit`**. |

## Out of scope (as specified)

- Network adjacency (**Iteration 25**). Posture / **`posture_maxvar`** (**Iteration 26**). Experiments (**Iteration 27**).

## Gate evidence

```bash
cd backend && uv run pytest --tb=short -q
# 152 passed, 1 skipped
```

Stress: **`test_stress_30_tier1_and_270_tier3_under_15s`** — 300 agents × 2 rounds, fake LLM, **`llm_concurrency_cap` 16**, wall clock **&lt; 15s** (local; Opus target was &lt; 10s on builder hardware).

## New tests (`tests/test_iteration24.py`)

| Test | Purpose |
|------|---------|
| `test_hybrid_core_remainder_synthetic_always_tier3` | PSLE principal + HoD + 2 synthetics → tiers `[1,2,3,3]`. |
| `test_tier3_heuristic_tracks_tier1_delta` | Principal Tier 1 + 1 synthetic Tier 3; LLM bumps support; Tier 3 moves with dampening 1.0, noise 0. |
| `test_stress_30_tier1_and_270_tier3_under_15s` | 30 × same principal persona + 270 synthetics; **`hybrid_core_remainder`**; 600 transcript rows. |

**Regression:** **`tests/test_iteration20.py`** — capabilities / API max **300**; **`test_agent_limit_300_accepted`**.

## Next

**Iteration 26** (before 25 per Opus build order): **`posture_maxvar`** — see [`HANDOFF_TO_BUILDER.md`](../handoffs/HANDOFF_TO_BUILDER.md#iteration-26-starter-pre-filled--2026-04-06).
