# Review: Iteration 27
Date: 2026-04-07
Reviewer: Claude Opus (Architect)
Verdict: PASS_WITH_ISSUES

## Iteration Delta

- New SQLite tables `experiments` and `experiment_runs`; nullable `simulation_runs.experiment_id`.
- Full experiment CRUD: `POST /experiments`, `GET /experiments`, `GET /experiments/{id}` (metadata + comparison table), `GET …/export.json`, `GET …/export.zip` (with `comparison.csv`).
- Frontend `ExperimentConsole` tab: create form, sparkline comparison, per-run status, recent experiments, two-run compare by ID.

## Critical Issues

None.

## Important Issues

### I1: `POST /experiments` blocks the HTTP connection for the entire experiment lifetime
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/api/experiments.py` (lines 268–315)
- Problem: The endpoint runs all child simulations **sequentially inside the request handler**. Each run can block up to 900 seconds (`wait_for_simulation_terminal` timeout). A 16-run experiment could hold the connection for hours. If the browser, reverse proxy, or network times out, the experiment continues server-side but the client loses the response — the `experiment_id` is never returned. The frontend has no cancel button or progress reporting during this wait.
- Fix (recommended — choose one):
  - **Option A (background task):** Return `{ experiment_id }` immediately with `status: "pending"`. Move the sequential run loop into `asyncio.create_task` (same pattern as `queue_simulation_run` → `run_simulation_task_guarded`). The frontend polls `GET /experiments/{id}` to watch per-run status updates — this endpoint already returns per-run status.
  - **Option B (lighter — defer Option A):** For now, add a hardcoded per-run timeout ceiling for experiment runs (e.g. 120s instead of 900s), and add a frontend progress poll: after the POST fires, start polling `GET /experiments/{id}` on a 2-second interval so the user sees partial progress even if the POST eventually times out. Swap the `fetch` to use `AbortController` + cancel button.

### I2: No test for experiment failure path
- Severity: IMPORTANT
- Files: `backend/tests/test_iteration27.py`
- Problem: The `except Exception` block in `create_experiment_endpoint` (line 311–313) sets `status = "failed"` and re-raises. This branch has zero test coverage. If a future refactor breaks it, experiments could get stuck in `"running"` forever.
- Fix: Add a test that monkeypatches `queue_simulation_run` (or `wait_for_simulation_terminal`) to raise an exception, then asserts:
  ```python
  row = asyncio.run(get_experiment_row(str(db), experiment_id=...))
  assert row["status"] == "failed"
  ```
  The HTTP response should be a 500. Confirm the experiment row has `completed_at` set.

### I3: `_series_key` and `_series_key_for_link` are near-duplicate functions
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/api/experiments.py` (lines 130–159)
- Problem: Both functions implement the same `base → deduplicate with __N suffix` algorithm with slightly different input shapes. Duplication risks drift and makes the deduplication logic harder to test in isolation.
- Fix: Extract a shared helper:
  ```python
  def _deduplicate_key(base: str, used: set[str]) -> str:
      key = base
      n = 1
      while key in used:
          n += 1
          key = f"{base}__{n}"
      used.add(key)
      return key
  ```
  Then both `_series_key` and `_series_key_for_link` compute `base` from their respective inputs and call `_deduplicate_key`.

## Minor Issues

### M1: Frontend has no cancel/abort for experiment runs
- Severity: MINOR
- Files: `frontend/src/components/ExperimentConsole.tsx` (line 82–105)
- Problem: Unlike `AgentConsole` (which has `AbortController` + Cancel button + elapsed timer), `ExperimentConsole` offers no way to cancel a running experiment. The user is stuck watching "Running experiment…" with no feedback.
- Fix: Add `AbortController` on the `createExperiment` fetch + a Cancel button + elapsed timer (same pattern as `AgentConsole`). Even without server-side abort, the client-side cancel frees the UI.

### M2: `set_experiment_status` has duplicated SQL branches
- Severity: MINOR
- Files: `backend/src/mirofish_backend/db/repo.py` (lines 1046–1064)
- Problem: The `completed` and `failed` branches execute identical SQL (`UPDATE … SET status = ?, completed_at = CURRENT_TIMESTAMP …`). The `else` branch is for non-terminal states.
- Fix: Collapse to:
  ```python
  if status in ("completed", "failed"):
      await db.execute(
          "UPDATE experiments SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?;",
          (status, experiment_id),
      )
  else:
      await db.execute(
          "UPDATE experiments SET status = ? WHERE id = ?;",
          (status, experiment_id),
      )
  ```

### M3: Experiment list doesn't expose run count
- Severity: MINOR
- Files: `backend/src/mirofish_backend/db/repo.py` (`list_experiments`), `frontend/src/components/ExperimentConsole.tsx`
- Problem: `GET /experiments` returns only the base experiment row. The frontend list shows name/status/id but not how many runs each experiment has. A researcher scanning old experiments has to click each one to see the run count.
- Fix: Add a `run_count` field via a `LEFT JOIN experiment_runs … GROUP BY` or a subquery in `list_experiments`. Surface in the frontend list item.

### M4: Comparison sparklines show only `implementation_readiness`
- Severity: MINOR
- Files: `frontend/src/components/ExperimentConsole.tsx` (lines 137–153, 260–268)
- Problem: The comparison data includes 5 metrics (`implementation_readiness`, `alignment_index`, `adoption_momentum`, `conflict_events`, `consistency_index`) but the sparkline section only visualizes `implementation_readiness`. Researchers need to compare all dimensions.
- Fix: Add a toggle or tabs to pick which metric to plot, or add a simple table view below the sparklines showing all metrics per round × series. Alternatively, render one sparkline row per metric.

### M5: No `DELETE /experiments` endpoint
- Severity: MINOR
- Files: `backend/src/mirofish_backend/api/experiments.py`
- Problem: No way to clean up old or failed experiments. Acceptable for MVP — backlog item.
- Fix: Add `DELETE /experiments/{experiment_id}` that removes the experiment row, experiment_run links, and optionally the child simulation_runs (or just unlinks them by nulling `experiment_id`).

## Architecture Alignment

| Component | Status | Gap |
|-----------|--------|-----|
| Orchestrator | ✅ | No change — experiments delegate to existing `queue_simulation_run` |
| LLM Router | ✅ | Unchanged |
| Memory System | ✅ | Unchanged |
| Prompt Architecture | ✅ | Unchanged |
| RAG Pipeline | ✅ | Unchanged |
| Persona System | ✅ | Unchanged |
| Validity Module | ✅ | Unchanged |
| Scenarios | ✅ | Shared `scenario_id` across experiment runs |
| Data Model | ✅ | Clean additive schema: `experiments`, `experiment_runs`, nullable `experiment_id` on `simulation_runs` |
| Frontend | ⚠️ | Functional but missing cancel/abort, multi-metric comparison, run count in list |
| Config/Reproducibility | ✅ | `config_snapshot.experiment` records experiment id, step index, label per run |
| Sampling Audit (Iter 22+) | ✅ | Each child run carries its own sampling audit — correct |
| Experiments (Iter 27) | ⚠️ | Blocking POST is the main design gap; see I1 |

## What's Good

- **Clean separation of concerns** — experiments are a persistence + comparison layer over `queue_simulation_run`, not a parallel orchestration path. Zero simulation logic duplicated.
- **`_merge_to_simulation_request`** elegantly merges experiment-level defaults with per-step overrides using Pydantic's `model_dump(exclude_none=True)`.
- **Comparison table** design is correct — round × series matrix from `global_state_snapshots` + `round_outcomes`.
- **Export ZIP** is well-structured — `comparison.csv` at root, `experiment.json` for metadata, per-run `export.json` + `bundle.zip` under `runs/{id}/`.
- **`experiment_id` backward compatibility** — nullable column, `_ensure_column` migration, standalone runs have NULL.
- **E2E test** covers the full lifecycle: create experiment → verify row → list links → get detail → get export.json → get export.zip → verify CSV contents.
- **Frontend** is functional and follows established patterns: form → submit → load detail → sparklines → download/export links.
- **Design decision documented** in HANDOFF: experiments ≠ agent orchestrator; experiments add persistence; agent layer remains stateless.

## Next Steps for Builder

### Priority 1 (hardening — do before next iteration)
1. **Add experiment failure test** (I2) — monkeypatch `queue_simulation_run` to raise; verify experiment status = `"failed"`.
2. **Unify `_series_key` helpers** (I3) — extract `_deduplicate_key` shared function.
3. **Add cancel + elapsed timer** to `ExperimentConsole` (M1) — reuse `AgentConsole` pattern.

### Priority 2 (recommended before grant demo)
4. **Background experiment execution** (I1) — move run loop to `asyncio.create_task`; return `experiment_id` immediately; frontend polls for progress.
5. **Multi-metric comparison view** (M4) — table or togglable sparklines for all 5 metrics.
6. **Run count in experiment list** (M3) — JOIN or subquery in `list_experiments`.

### Priority 3 (backlog)
7. Collapse `set_experiment_status` branches (M2).
8. `DELETE /experiments/{id}` endpoint (M5).

## Test Requirements

For post-27 hardening to pass:
1. Existing `test_iteration27.py` (4 tests) continue passing.
2. New: `test_experiment_failure_sets_status_failed` — monkeypatch raises in run loop; experiment row has `status == "failed"` and `completed_at` set.
3. New: `test_series_key_deduplication` — duplicate labels produce `label`, `label__2`, `label__3`.
4. Frontend: `npm run build` passes after cancel/abort addition.
