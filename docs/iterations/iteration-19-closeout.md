# Iteration 19 closeout — Parallel LLM execution

**Date:** 2026-04-06  
**Status:** Shipped — **Architect PASS 2026-04-06** (see `HANDOFF_TO_BUILDER.md` § *Iteration 19 — PASS*); follow-up items 1–3 addressed in same pass.  
**Theme:** Replace sequential per-turn LLM calls within a round with `asyncio.gather` + `asyncio.Semaphore`, bounded by a configurable concurrency cap.

## Shipped

| Item | Detail |
|------|--------|
| **`simulation/orchestrator.py`** | `run_simulation_task` accepts `llm_concurrency_cap: int = 4`. A single `asyncio.Semaphore(llm_concurrency_cap)` is created before the round loop. Per-round: `turn_assignments` pre-assigns `(turn_index, agent)` pairs **before** dispatch; a nested `_run_one_turn` coroutine wraps all per-turn logic under `async with sem:`; `asyncio.gather(*tasks, return_exceptions=True)` dispatches all turns for a round concurrently. |
| **Turn index pre-assignment** | `turn_assignments = list(enumerate(round_agents, start=1))` is computed before the gather, so `_build_interaction_plan` and `interaction_last_k` are deterministic regardless of execution order. |
| **Rounds remain sequential** | The `for round_number` loop only advances after `await asyncio.gather(...)` returns. Round N uses only prior-round DB context (correct by design — same-round parallel turns see no same-round peers). |
| **Per-turn error isolation** | LLM errors within `_run_one_turn` are caught and stored as `[LLM error] …` response strings. Catastrophic errors that escape the per-turn try/except are caught by `return_exceptions=True`; the failing turn is logged at ERROR level and the round continues. |
| **State dict safety** | Each agent has a unique key in `agent_states`; asyncio is single-threaded so reads and writes are safe without locks. |
| **`config.py`** | `LLM_CONCURRENCY_CAP: int = 4` env var. |
| **`api/simulations.py`** | `SimulationRunRequest.llm_concurrency_cap: int \| None` (1–16, default `None` → server default). Effective cap resolved as `_req.llm_concurrency_cap ?? settings.llm_concurrency_cap`. Stored in `config_snapshot["llm_concurrency_cap"]`. Passed through `run_simulation_task_guarded` → `run_simulation_task`. |
| **`api/capabilities.py`** *(follow-up 1)* | `build_capabilities_dict()` includes `simulation_run.llm_concurrency_cap: {default: 4, min: 1, max: 16}`. Planner LLM vocabulary is complete. |
| **`agent/orchestrator.py`** *(follow-up 2)* | `PlanSimulationParams` gains `llm_concurrency_cap: int \| None` (ge=1, le=16). `_simulation_run_request` passes it through. `validate_plan_against_capabilities` checks range against capabilities dict. Planner system prompt includes `"llm_concurrency_cap": null` in the JSON shape. |
| **Per-round wall-clock log** *(follow-up 3)* | `logger.info("round_complete ... turns=%d failed=%d wall_ms=%d")` emitted after each `asyncio.gather` round. `failed_turns` counter tracks catastrophic escaping errors alongside normal conflict events. |

## Architect PASS notes (non-blocking — items 4–5 documented)

- **Item 4 (DB-level error transcript gap):** if an exception escapes the inner try/except inside `_run_one_turn` (e.g., `insert_agent_turn` DB write failure), `return_exceptions=True` catches it and logs at ERROR but no row is written. `len(transcript)` may be less than `agents × rounds` when DB-level errors occur — this is visible in the `failed=N` field of the `round_complete` log line. Researchers should treat the transcript count as a lower bound, not an exact value, when DB errors are logged.
- **Item 5 (`aiosqlite` write batching):** aiosqlite serializes writes at current scale (≤50 agents, cap ≤16). At Iteration 20+ population scale (100+ agents), collecting turn rows per round and using `executemany` after gather would reduce write round-trips. Deferred to Iteration 20+.

## Not in scope (defer)

- Parallel runs across multi-run agent plans (Iteration 20+).
- Network/edges artefact.
- DB sharding or connection pool for write contention > current scale.

## Gate evidence

```bash
cd backend && uv run pytest tests/ -q
# 117 passed, 1 skipped (manual SSE placeholder)
cd ../frontend && npm run build   # unchanged, still passes
```

## New tests (`tests/test_iteration19.py`)

| Test | What it verifies |
|------|-----------------|
| `test_parallel_execution_all_turns_written` | cap=4, 4 agents × 2 rounds → 8 turns, status=completed |
| `test_sequential_and_parallel_produce_same_turn_order` | cap=1 vs cap=4, same seed → identical (round, turn_index, agent_id, interaction_type) per slot |
| `test_error_isolation_one_llm_failure_does_not_abort_round` | LLM raises on turn 2; all 3 turns written; failing turn has `[LLM error]` prefix; status=completed |
| `test_stress_40_turns_parallel_completes_quickly` | 8 agents × 5 rounds = 40 turns; fake instant LLM; elapsed < 5 s |
| `test_api_concurrency_cap_stored_in_config_snapshot` | `POST /simulations/run` with `llm_concurrency_cap=3` → stored in config_snapshot |
| `test_api_default_concurrency_cap_in_config_snapshot` | Omitting cap → server default (4) stored |
| `test_api_concurrency_cap_out_of_range_rejected` | `llm_concurrency_cap=0` → 422 |

## Design notes

- **`cap=1` is strictly sequential** — `Semaphore(1)` allows exactly one coroutine at a time; reproduces pre-Iteration-19 behaviour for debugging or cost-sensitive runs.
- **`aiosqlite` write contention**: aiosqlite serializes writes internally; parallel turns completing simultaneously queue. Acceptable at ≤50 agents; noted for future if DB bottleneck appears.
- **`interaction_last_k` for turn_index 1**: first speaker in the pre-ordered list still gets the wider peer-context window, as in sequential mode. The wider window applies to the DB query that sees only prior-round turns.
- **Closure safety**: `_run_one_turn` captures `round_agents`, `round_number`, `policy_event` by closure. Safe because `await asyncio.gather(...)` ensures all tasks complete before the outer loop advances.
