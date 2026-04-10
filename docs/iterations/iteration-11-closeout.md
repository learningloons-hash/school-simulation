# Iteration 11 closeout

**Project:** `mirofish-mvp`  
**Gate date:** 2026-04-02  
**Theme:** Single **population-table** contract — pool CSV, **weighted** / **stratified** draw, **`AgentContextV1`** alignment, **`config_snapshot` provenance**.

## Shipped

| Item | Detail |
|------|--------|
| Schema | `population_schema_version` **`1`** (`POPULATION_SCHEMA_VERSION` in [`population/csv_population.py`](../../backend/src/mirofish_backend/population/csv_population.py)). |
| CSV columns | `persona_id` (required), `sampling_weight`, `stratum`, `age`, `sex`, `ethnicity`, `ses`, `name`, `groups` (pipe-separated). |
| Draw | Without replacement; `random.Random(random_seed & 0xFFFFFFFF)` dedicated to population draw. Modes: **`weighted`**, **`stratified`** (largest-remainder quotas per `stratum`). |
| API | `POST /simulations/run`: `population_csv`, `population_sample_mode`. `GET /simulations/population-csv-template`. |
| Merge order | **Population draw first** → optional **roster CSV** merges per 1-based slot on top (`merge_persona_for_slot`). |
| Demographics | Population row fields override synthetic `_build_demographics` via `demographic_overrides` into orchestrator. |
| `config_snapshot` | `population_*` fields, `population_draw` trace (slot, file line, `csv_row_index`, `persona_id`, `stratum`, weight), `population_merge_order`, `population_data_provenance`, `population_thesis_note`. |
| UI | Run tab: population textarea + template link + sample mode; Live tab shows population summary. |

## Validation policy

- Unknown `persona_id` → **422** with line number.
- Unknown `groups` id → row accepted; id listed in `population_unknown_group_ids` (same as roster).
- `sampling_weight` ≤ 0 → **422**.
- Pool row count &lt; `agent_limit` → **422**.
- Stratified: if a stratum’s quota exceeds its row count → **ValueError** (API → **422**). Covered by `test_stratified_raises_when_stratum_quota_exceeds_row_count` (monkeypatched quota; guards regressions).

## Thesis / representativeness

Engine does not assert empirical representativeness. `population_thesis_note` in `config_snapshot` states that pool provenance and any site overlay (e.g. Trinidad school context) are **analyst claims**. Core fields map to **IAD-neutral** `AgentContextV1` demographics / `group_ids`.

## Not in scope (defer)

- Second population file format (extensions must version under the same contract).
- Network / edges artefact (ADR-001 add-on; same versioning story when added).
- DB column for population row id per turn (trace lives in `config_snapshot`).

## Gate evidence

```bash
cd backend && PYTHONPATH=src pytest tests/ -q
cd ../frontend && npm run build
```

## Self-check — `ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md` § Iteration 11

Mapped verbatim for sign-off speed:

- [x] **One contract only** for population import (`population_schema_version` included) — **`1`** in code + `config_snapshot`.
- [x] **Validation policy documented** — required vs optional fields, defaults (`sampling_weight` 1.0, empty `stratum`), errors — see **Validation policy** above.
- [x] **Weighted/stratified sampling ties to same context keys** used in Iteration 10 interface — `persona_id` → template; `age`/`sex`/`ethnicity`/`ses`/`groups` → `AgentContextV1` / persona merge.
- [x] **No second competing format** — single CSV dialect; extensions version under same ADR.
- [x] **Traceability fields** — `population_draw`, `population_data_provenance`, `population_merge_order`, unknown `group_ids` list.
- [x] **Thesis alignment note** — `population_thesis_note` + § **Thesis / representativeness** above (IAD core vs analyst/site overlay).
