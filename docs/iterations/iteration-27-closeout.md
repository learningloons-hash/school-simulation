# Iteration 27 closeout — Multi-run experiments

**Not** **Senna `senna-iter-27`** (Arc 6 *Context bounding* — a separate counter; see [`HANDOFF_SENNA_ARC6.md`](../handoffs/HANDOFF_SENNA_ARC6.md) **`## senna-iter-27`**; closeout `docs/iterations/senna-iter-27-closeout.md` when shipped). This file is the **thesis / platform** experiments iteration.

**Date:** 2026-04-07  
**Theme:** Persisted **experiments** (shared `scenario_id` + `random_seed`); **sequential** child simulation runs; **comparison** table + exports; **Experiments** UI (replaces standalone **Compare runs** tab).

## Shipped

| Area | Detail |
|------|--------|
| **DB** | Tables **`experiments`**, **`experiment_runs`**; nullable **`simulation_runs.experiment_id`** (migration via `_ensure_column`). |
| **`api/experiments.py`** | **`POST /experiments`**, **`GET /experiments`**, **`GET /experiments/{id}`** (metadata + per-run status + **`comparison`** by round), **`GET …/export.json`**, **`GET …/export.zip`** (`comparison.csv` + `experiment.json` + per-run `runs/{id}/export.json` + `bundle.zip`). |
| **`queue_simulation_run`** | Optional **`experiment_id`**, step/label metadata in **`config_snapshot.experiment`**; **`run_display_name`** for run list. |
| **`export_bundle.py`** | **`experiment_comparison_csv_bytes`** for long-form CSV. |
| **`GET /capabilities`** | **`experiments`** object (limits, statuses, endpoint paths). |
| **`GET /simulations`** | **`experiment_id`** on each list row when set. |
| **Frontend** | **`ExperimentConsole`**: create form (scenario, seed, rounds, multi strategy rows), comparison **Sparklines** with metric **select** (all five comparison fields), **details** table “all metrics by round”, per-run status, recent experiments (with **`run_count`**), **Cancel** + elapsed timer + **`AbortSignal`** on create, **compare two runs by ID** (absorbed from old Compare tab). |

## Post–Iteration 27 hardening (2026-04-07)

Architect **PASS_WITH_ISSUES** follow-ups from [`review-iteration-27.md`](../reviews/review-iteration-27.md):

| Item | Change |
|------|--------|
| **Failure path** | `create_experiment_endpoint`: on exception, **`set_experiment_status(…, failed)`** then **`HTTPException(500)`** (stable client response; **`completed_at`** set). Test: **`test_experiment_failure_sets_status_failed`**. |
| **Dedup helper** | **`_deduplicate_key`**; **`_series_key`** / **`_series_key_for_link`** delegate. Test: **`test_deduplicate_key_collision_suffix`**. |
| **Repo** | **`set_experiment_status`**: single SQL branch for **`completed`** / **`failed`**; **`list_experiments`**: **`run_count`** subquery on **`experiment_runs`**. Test: **`test_list_experiments_includes_run_count`**. |
| **Blocking POST** | Documented in **`api/experiments.py`** module docstring (background job + polling = backlog). |
| **API client** | **`createExperiment(..., signal?)`** forwards **`AbortSignal`** to **`fetch`**. |

## Behaviour notes

- Runs in one experiment execute **one after another** (`wait_for_simulation_terminal` between queues). Long experiments may require a patient client timeout.
- Experiment row **`status`**: **`failed`** if the POST handler hits an error before finishing the loop (experiment marked failed and **HTTP 500** returned); individual simulation failures still leave the experiment **`completed`** (per product spec).
- **`comparison`** keys are **series keys** (labels or `strategy_index`); duplicate labels are disambiguated with `__N` suffix on create and on read.

## Gate evidence

```bash
cd backend && uv run pytest --tb=no -q
# 180 passed, 1 skipped
cd ../frontend && npm run build
```

## Tests

**`tests/test_iteration27.py`** — standalone run **`experiment_id`** null; E2E **POST /experiments** (two strategies, fake LLM); export ZIP contains **`comparison.csv`**; capabilities meta; post-27: dedupe helper, failure → **`failed`** + **500**, **`run_count`** on **GET /experiments**.

## Next

Product backlog: parallel experiment dispatch; experiment-scoped UI polish; **`network_centrality`** rows in UI with **`network_csv`** editor.
