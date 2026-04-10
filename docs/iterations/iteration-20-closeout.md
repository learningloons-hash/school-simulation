# Iteration 20 closeout — Population Scale and Cohort Aggregation

**Date:** 2026-04-06  
**Status:** Shipped — pending architect review.  
**Theme:** Lift the `agent_limit` ceiling to 200, add post-processing cohort aggregation to the export bundle (`export_version` 5), record aggregation settings in `config_snapshot`, and write a thesis-grade 500-agent feasibility note.

## Shipped

| Item | Detail |
|------|--------|
| **`api/simulations.py` — limits raised** | `agent_limit` `le=50` → `le=200`. `speakers_per_round` `le=50` → `le=200`. |
| **`api/simulations.py` — `aggregation_threshold`** | New field `aggregation_threshold: int = Field(default=20, ge=1, le=200)`. Controls the agent count above which cohort aggregation is semantically meaningful. |
| **`api/simulations.py` — `config_snapshot`** | Adds `"aggregation_threshold"` (the requested value) and `"aggregation_mode"` (`True` when `agent_limit >= aggregation_threshold`, else `False`). |
| **`api/simulations.py` — export.json version 5** | `export_simulation_json` now returns `"export_version": "5"` and `"cohort_summary": compute_cohort_summary(...)`. Import added: `from mirofish_backend.export_bundle import build_export_zip, compute_cohort_summary`. |
| **`export_bundle.py` — `compute_cohort_summary`** | Pure function. Groups `agent_state_snapshots` by `(group_id, round_number)`. For each bucket: `agent_count`, `spoke_count`, `avg_support_level`, `avg_resistance_level`, `avg_workload_stress`. Agents with no `group_ids` (empty list, missing, or `"[]"`) aggregate under `group_id: ""`. No new DB query — reads from the already-fetched bundle. |
| **`export_bundle.py` — ZIP** | `build_export_zip` now writes `cohort_summary.csv` (columns: `group_id, round_number, agent_count, spoke_count, avg_support_level, avg_resistance_level, avg_workload_stress`). Module docstring updated: `"5" — cohort_summary`. |
| **`agent/orchestrator.py` — `PlanSimulationParams`** | `agent_limit` `le=50` → `le=200`. `speakers_per_round` `le=50` → `le=200`. `aggregation_threshold: int = Field(default=20, ge=1, le=200)` added. `_simulation_run_request` forwards `aggregation_threshold=sim.aggregation_threshold`. Planner system prompt JSON shape includes `"aggregation_threshold": 20`. |
| **`api/capabilities.py`** | `build_capabilities_dict()` gains `"agent_limit": {"default": 3, "min": 1, "max": 200}` and `"aggregation_threshold": {"default": 20, "min": 1, "max": 200}` under `"simulation_run"`. |
| **`docs/plans/scale-feasibility-500-agent.md`** | Thesis-grade note: turn-count model, wall-clock latency table at 50/100/200/500 agents with concurrency-cap projections, Anthropic token budget (hybrid vs full-cloud), DB write patterns, cohort aggregation cost, recommended configs per tier, hard API limits table. |

## Not in scope (defer)

- `aiosqlite` batch inserts (`executemany` per round) — tracked in Iteration 19 closeout § Item 5; not a blocker at 200-agent ceiling.
- SQLite WAL mode — required before 500-agent runs; noted in feasibility doc.
- Multi-run parallelism across an agent plan's `runs[]` array (separate from per-round LLM parallelism in Iteration 19).

## Architecture note

Cohort aggregation is a **post-processing view** on export, not a simulation-time concept. The full `agent_state_snapshots` table is always written per turn; `compute_cohort_summary` aggregates at export time. This keeps the simulation engine unchanged and raw data always available for re-analysis.

`aggregation_mode` in `config_snapshot` is a researcher convenience flag: it records whether the run crossed the aggregation threshold at request time, so analysts can quickly identify which runs warrant cohort-level interpretation.

## Gate evidence

```bash
cd backend && pytest --tb=short -q
# 125 passed, 1 skipped
cd ../frontend && npm run build   # no frontend changes
```

## New tests (`tests/test_iteration20.py`)

| Test | What it verifies |
|------|-----------------|
| `test_compute_cohort_summary_groups_correctly` | Two-group snapshot set → correct per-round `agent_count`, `spoke_count`, `avg_support_level`, `avg_resistance_level` per group |
| `test_compute_cohort_summary_ungrouped_agents` | Empty `group_ids` → single entry with `group_id: ""`, correct `avg_support_level` |
| `test_export_json_has_cohort_summary_and_version_5` | Export payload shape: `export_version == "5"` and `cohort_summary` list present with correct `agent_count` |
| `test_export_zip_contains_cohort_summary_csv` | ZIP includes `cohort_summary.csv`; header correct; 1 data row for 1-group run |
| `test_agent_limit_200_accepted` | `POST /simulations/run` with `agent_limit=200` → 200 OK |
| `test_aggregation_fields_in_config_snapshot` | `aggregation_threshold=20`, `agent_limit=50` → `aggregation_mode=True` in config_snapshot |
| `test_aggregation_mode_false_below_threshold` | `agent_limit=5`, `aggregation_threshold=20` → `aggregation_mode=False` |
| `test_capabilities_includes_agent_limit_range` | `GET /capabilities` → `agent_limit.max == 200`, `aggregation_threshold.default == 20` |

## Design notes

- **`group_ids` serialisation:** `compute_cohort_summary` handles both list and JSON-string forms of `group_ids` (the DB stores JSON text; the export bundle typically deserialises it before passing to the function, but the guard is belt-and-suspenders).
- **Multi-group agents:** an agent in both `["leadership", "teachers"]` contributes to **both** cohort buckets. This is intentional — it mirrors how group membership is used in the visibility policy.
- **Empty cohort_summary:** when no `agent_state_snapshots` exist (e.g. a pending run) `compute_cohort_summary([])` returns `[]`. The export.json key is still present.
