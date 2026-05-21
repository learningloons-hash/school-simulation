# Senna iter-35 closeout — Planner Parity + Arc 7 Cleanup

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC8.md`](../handoffs/HANDOFF_SENNA_ARC8.md) **`## senna-iter-35`**.  
**Date:** 2026-05-19

## Shipped

- **Agent planner parity:** optional `model_profile_id` on `PlanSimulationParams`; forwarded through `_simulation_run_request` → `SimulationRunRequest`; planner JSON template and `validate_plan_against_capabilities` updated.
- **Tier-3 provenance:** Tier-3 heuristic turns persist `effective_profile_id="heuristic"` (`HEURISTIC_PROFILE_SENTINEL` in `llm/routing_policies.py` — sentinel, not a built-in profile).
- **Arc 7 test cleanup:** queue-run tests replace `create_task` `return_value=None` with `_discard_create_task` that closes the scheduled coroutine (no “coroutine was never awaited” / async mock resource warnings).

## Files touched

- `backend/src/mirofish_backend/agent/orchestrator.py`
- `backend/src/mirofish_backend/llm/routing_policies.py`
- `backend/src/mirofish_backend/simulation/orchestrator.py`
- `backend/tests/test_iteration17.py`
- `backend/tests/test_iteration23.py`
- `backend/tests/test_model_profiles.py`
- `backend/tests/test_senna_arc7_hardening.py`

## Verification

- `uv run pytest` (from `backend/`): **249 passed, 1 skipped**
- New coverage: planner forwards `model_profile_id` to queue; invalid profile rejected at plan validation; Tier-3 export row has `effective_profile_id=heuristic`

## Next

- **senna-iter-36** — profile registry + model capability metadata (`HANDOFF_SENNA_ARC8.md` § senna-iter-36)
