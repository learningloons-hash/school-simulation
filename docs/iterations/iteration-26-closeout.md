# Iteration 26 closeout

**Project:** `mirofish-mvp`  
**Feature gate:** 2026-04-06  
**Post–architect hardening gate:** 2026-04-07  

**Theme:** **`implementation_posture`** (opaque string), **`posture_maxvar`** sampling strategy, **`GET /simulations/{id}/sampling-report`**, CSV + YAML examples, capabilities.

## Gate status

| Milestone | Architect | Builder handoff |
|-----------|-----------|-----------------|
| Feature ship | — | [`HANDOFF_TO_BUILDER.md` § Iteration 26 starter](../handoffs/HANDOFF_TO_BUILDER.md#iteration-26-starter-pre-filled--2026-04-06) — DoD **[x]** |
| Review | **PASS_WITH_ISSUES** — [`review-iteration-26.md`](../reviews/review-iteration-26.md) | Follow-ups tracked under [Post-Iteration 26 hardening](../handoffs/HANDOFF_TO_BUILDER.md#post-iteration-26-hardening-pre-filled--2026-04-07) |
| Hardening | *(resolved in repo)* | Same § — Definition of done **all [x]** (2026-04-07) |

**Iteration 26 is closed:** no remaining items in `HANDOFF_TO_BUILDER.md` for this iteration. Next numbered build: **Iteration 25** (network + **ADR-002**).

## Shipped (core)

| Item | Detail |
|------|--------|
| Persona | `PersonaTemplate.implementation_posture` optional string; YAML + embedded fallbacks (`registry.py`). |
| Roster / population | Optional column `implementation_posture`; merge overlays **non-empty** values only (`roster/csv_roster.py`, `population/csv_population.py`). |
| Strategy | `posture_maxvar`: Tier 1 = one slot per distinct non-empty posture (slot order); remainder split like role-stratified remainder logic; **no tags** → fallback with rationale prefix `posture_maxvar (no posture tags; role_stratified):` (`simulation/sampling_strategy.py`). |
| Audit | `build_sampling_audit_extended` adds `role` and `implementation_posture` on each `per_agent` row (new runs). |
| Report | `simulation/sampling_report.py` → `build_sampling_report_json`; **`centrality`** reserved (`null` until network data in **Iteration 25**). |
| API | `GET /simulations/{simulation_id}/sampling-report` — **404** missing run, **409** if `pending`/`running`, **400** if snapshot lacks `sampling_audit`. |
| Repo | `get_simulation_status_and_config_snapshot` light read (`db/repo.py`). |
| Templates | `ROSTER_CSV_TEMPLATE` / `POPULATION_CSV_TEMPLATE` include `implementation_posture` (`api/simulations.py`). |
| YAML | `psle_reform_mvp` + `fsbb_comparator` — ≥2 personas with example postures each. |
| Validation | `validate_scenario_document`: `implementation_posture` must be string when present. |
| Capabilities | `simulation_run.implementation_posture` meta; `sampling_strategies` includes `posture_maxvar`. |
| Agent planner | `PlanSimulationParams` accepts `posture_maxvar` with aligned error text. |

## Shipped (post–architect hardening, 2026-04-07)

| Item | Detail |
|------|--------|
| Docs | `SESSION_STATE.md` — Gate Evidence **164** tests, **§ Iteration 26 (Completed)**, Next focus → **25** only. |
| Test | `test_posture_maxvar_queued_run_audit_and_sampling_report` — queued run, fake LLM, audit + sampling-report JSON. |
| Template comment | Roster CSV: empty / whitespace **`implementation_posture`** does **not** clear YAML posture. |
| UI | Run tab + Run metadata: **Sampling report (JSON)** link for completed/failed runs (`samplingReportUrl` in `frontend/src/lib/api.ts`). |

## Gate evidence

```bash
cd backend && uv run pytest --tb=no -q
# 164 passed, 1 skipped (2026-04-07)
cd ../frontend && npm run build
```

## Handoff to Iteration 25

- **Spec:** [`HANDOFF_TO_BUILDER.md` — Iteration 25 starter](../handoffs/HANDOFF_TO_BUILDER.md#iteration-25-starter-pre-filled--2026-04-06) (**cold start** reading order is in that block).
- **Contract:** [`ADR-002-interaction-visibility.md`](../adr/ADR-002-interaction-visibility.md).
- **This iteration defers to 25:** `sampling_report` **`centrality`** field; unknown-agent handling for **`network_csv`**; **`network_centrality`** strategy; **`network_bounded`** / **`round_participants_only`** visibility.

## Follow-ups (product / later)

- Older runs may have `per_agent` rows without `role` / `implementation_posture`; report maps missing posture to `(untagged)` and role to `(unknown)`.
