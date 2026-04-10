# Review: Iteration 28
Date: 2026-04-07
Reviewer: Claude Opus (Architect)
Verdict: PASS_WITH_ISSUES

## Follow-up resolution (2026-04-08)

Builder hardening applied: **I1** `ExperimentCreateRequest` + merge to child runs + E2E test; **I2** `PlanSimulationParams`, `_simulation_run_request`, `validate_plan_against_capabilities`, planner JSON template; **I3** streak-reset test (varying fake LLM); **M2** `convergence_delta` in `get_merged_round_metrics`, comparison table, `comparison.csv`; **M3** `converged_at_round` on experiment run rows + UI; **M1** skip agents missing from `prev` in `_population_convergence_delta`. Suite **186 passed, 1 skipped**.

## Iteration Delta

- New convergence stopping criterion: `convergence_threshold` (float, optional) + `convergence_patience` (int, default 2) on `SimulationRunRequest`.
- Per-round `convergence_delta` (mean abs attitude change across agents) computed from round 2 onward, persisted on `global_state_snapshots`.
- `converged_at_round` on `simulation_runs` row + `config_snapshot`. Export version bumped to `7`.
- Live dashboard shows convergence delta sparkline + "Converged at round N" banner.

## Critical Issues

None.

## Important Issues

### I1: Convergence fields missing from `ExperimentCreateRequest` and `ExperimentRunStep`
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/api/experiments.py` (lines 49–79, 82–101)
- Problem: Neither `ExperimentCreateRequest` nor `ExperimentRunStep` includes `convergence_threshold` or `convergence_patience`. Since `_merge_to_simulation_request` merges experiment-level base fields with per-step overrides into a `SimulationRunRequest`, experiments cannot use the convergence stopping criterion. The thesis methodology requires running experiments (same scenario, multiple strategies) with convergence — this is the primary use case. A researcher would have to run individual simulations manually rather than using the experiment framework.
- Fix: Add `convergence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)` and `convergence_patience: int = Field(default=2, ge=1, le=25)` to `ExperimentCreateRequest` (base-level, shared across runs). No need to add per-step overrides — convergence parameters should be consistent across an experiment so cross-strategy comparison is fair.

### I2: Convergence fields missing from `PlanSimulationParams` (agent orchestrator)
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/agent/orchestrator.py` (lines 40–95)
- Problem: `PlanSimulationParams` has no `convergence_threshold` or `convergence_patience` fields. Runs dispatched via `POST /agent/ask` or `POST /agent/execute` cannot use convergence. The planner LLM cannot include convergence in generated plans even though `GET /capabilities` documents it.
- Fix: Add both fields to `PlanSimulationParams` (optional, same validators). Forward them through `_simulation_run_request`. Also update `validate_plan_against_capabilities` to accept these fields.

### I3: No test for convergence patience reset (streak broken then resumed)
- Severity: IMPORTANT
- Files: `backend/tests/test_iteration28.py`
- Problem: The existing early-stop test uses a fake LLM that returns **identical state every round** (`support_level: 0.52` etc.), so `convergence_delta` is 0.0 from round 2 onward and the streak is never broken. There is no test that verifies `conv_streak` resets to 0 when a round exceeds the threshold. A bug in the streak reset (e.g. incrementing instead of resetting) would pass all current tests.
- Fix: Add a test with a fake LLM that returns varying state for the first few rounds (above threshold) then stabilises. Verify that the simulation runs past the first sub-threshold round and only stops after `patience` consecutive sub-threshold rounds.

## Minor Issues

### M1: `_population_convergence_delta` silently skips agents missing from `prev`
- Severity: MINOR
- Files: `backend/src/mirofish_backend/simulation/orchestrator.py` (lines 235–250)
- Problem: If an `agent_id` is in `agents` but not in `prev` (e.g. synthetic remainders added mid-run — not currently possible but defensively), `prev[ag.agent_id]` raises `KeyError`. The function has no guard for this.
- Fix: Add a `if ag.agent_id not in prev: continue` guard or document the pre-condition in the docstring.

### M2: Convergence delta not in `get_merged_round_metrics` (experiment comparison)
- Severity: MINOR
- Files: `backend/src/mirofish_backend/db/repo.py` (`get_merged_round_metrics`, ~line 1159)
- Problem: `get_merged_round_metrics` (used to build the experiment comparison table) queries `global_state_snapshots` for `implementation_readiness` and `alignment_index` but does **not** fetch `convergence_delta`. The experiment comparison table therefore lacks the convergence metric per round. For the thesis, this means you can't see which strategy converged faster directly in the comparison view.
- Fix: Add `convergence_delta` to the `get_merged_round_metrics` query and include it in the comparison table rows. Also add it to `_build_comparison_table` in `experiments.py` and `_flatten_comparison_for_csv`.

### M3: Frontend Experiments tab doesn't show `converged_at_round` per run
- Severity: MINOR
- Files: `frontend/src/components/ExperimentConsole.tsx`
- Problem: The per-run status list in `ExperimentConsole` shows `series_key`, `sampling_strategy`, `status`, and `simulation_id` — but not whether the run converged early or ran full rounds. For a convergence-enabled experiment, the researcher needs to see at a glance which strategies converged and at which round.
- Fix: Add `converged_at_round` to the run detail fetched in `_experiment_detail_payload` and display it in the per-run status list item (e.g. "Converged at R14" or "Full 18 rounds").

### M4: `SESSION_STATE.md` already updated correctly
- Severity: MINOR (positive)
- No fix needed. Gate evidence shows 183 tests, export version 7, convergence fields documented.

## Architecture Alignment

| Component | Status | Gap |
|-----------|--------|-----|
| Orchestrator | ✅ | Convergence check after each round is clean; streak + patience logic correct |
| LLM Router | ✅ | Unchanged |
| Memory System | ✅ | Unchanged |
| Prompt Architecture | ✅ | Unchanged |
| RAG Pipeline | ✅ | Unchanged |
| Persona System | ✅ | Unchanged |
| Validity Module | ✅ | Unchanged |
| Scenarios | ✅ | Unchanged |
| Data Model | ✅ | `convergence_delta` on `global_state_snapshots`, `converged_at_round` on `simulation_runs` — clean additive |
| Frontend | ✅ | Run form inputs, Live tab sparkline + banner — clean |
| Config/Reproducibility | ✅ | `convergence_threshold`, `convergence_patience`, `converged_at_round` all in `config_snapshot` |
| Sampling Audit | ✅ | Unchanged |
| Experiments (Iter 27) | ⚠️ | Convergence not wired through experiment or agent orchestrator APIs |

## What's Good

- **`_population_convergence_delta` is a clean pure function** — no side effects, operates on in-memory state, returns `float | None`. Easy to test in isolation if needed.
- **Round 1 skip is correct** — no prior snapshot exists, so no delta is computed and the streak doesn't advance. This prevents false early stops.
- **Convergence is fully opt-in** — omitting `convergence_threshold` preserves existing `total_rounds` behavior exactly. Zero regressions.
- **The `merge_simulation_config_snapshot` approach for `converged_at_round`** is smart — it updates only the convergence field in the already-persisted `config_snapshot` JSON, avoiding a full rewrite of the snapshot.
- **Frontend implementation is clean** — convergence threshold/patience as optional fields in the Run form, sparkline in the Live tab, green banner on convergence. The banner also shows the threshold and patience values for at-a-glance audit.
- **Export version 7** is additive — old consumers ignore the new fields; `global_state_snapshots.csv` includes `convergence_delta` column.
- **Known limitation is documented** — Tier-3 heuristic dampening may cause premature convergence. This is the right call: document for thesis interpretation rather than adding complexity.

## Next Steps for Builder

### Priority 1 (hardening — do before Iteration 29)
1. **Wire convergence into experiments** (I1) — add fields to `ExperimentCreateRequest`, test with a convergence-enabled experiment sweep.
2. **Wire convergence into agent orchestrator** (I2) — add fields to `PlanSimulationParams` + forwarding + validation.
3. **Add streak-reset test** (I3) — fake LLM with varying output, verify patience is respected.

### Priority 2 (recommended)
4. **Add `convergence_delta` to experiment comparison table** (M2) — query + CSV column.
5. **Show `converged_at_round` in experiment per-run list** (M3).

### Priority 3 (backlog)
6. Defensive guard in `_population_convergence_delta` (M1).

## Test Requirements

For post-28 hardening to pass:
1. Existing `test_iteration28.py` (3 tests) continue passing.
2. New: experiment with `convergence_threshold` creates runs that converge (builds on `test_iteration27.py` pattern).
3. New: streak-reset test — fake LLM alternates between stable and unstable rounds; convergence only fires after true patience-length streak.
4. Frontend: `npm run build` passes.
