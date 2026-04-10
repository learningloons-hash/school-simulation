# Scenario analyst wizard — design (MVP)

## Storage (locked for MVP)

- **SQLite table `user_scenarios`:** `scenario_id` (PK), `display_name`, `document_json` (full YAML-shaped document), `scenario_doc_version` (default `1`), `updated_at`.
- **Resolution order** for `load_scenario_for_run(sqlite_path, scenario_id)`: **(1)** row in `user_scenarios`, else **(2)** package registry (`scenarios/data/*.yaml` + embedded fallback).

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/scenarios` | Catalog: `{ id, name, rag_enabled, source }` for builtin + user |
| POST | `/scenarios` | Create user scenario; body = document + optional `display_name`; response `{ id, warnings[] }` |
| PUT | `/scenarios/{scenario_id}` | Replace user scenario (must exist) |
| POST | `/scenarios/clone` | `{ template_id, new_scenario_id }` → copy builtin or user template |
| GET | `/scenarios/{scenario_id}/export.yaml` | Download YAML (user or materialized builtin) |
| GET | `/scenarios/bundled-rag-paths` | List safe corpus paths under `scenarios/data/` for wizard multiselect |

**Note:** `GET /simulations` remains **simulation runs** list; scenario catalog is **`/scenarios`**.

## Document shape

Same as existing YAML: `scenario_id`, `name`, `policy_events` (object round→string), `personas[]`, optional `groups[]`, optional `rag_enabled`, `rag_corpus_paths[]`.

## Validation

- **422** on hard errors: bad slug, missing required fields, invalid persona structure, `new_scenario_id` already exists (POST), unknown template (clone).
- **`warnings[]`** on success: e.g. persona `groups` reference unknown `group_id`; `scenario_id` matches a **builtin** id while saving as user (**shadows** package default for this DB).

## RAG in wizard

- **Paths only:** `rag_corpus_paths` must be chosen from **bundled files** under `scenarios/data/` (server-enumerated). Per-run corpus **upload** remains a separate future feature.

## Run integration

- `POST /simulations/run` uses `load_scenario_for_run`; `config_snapshot` includes `scenario_source`: `user` | `builtin`.

## Frontend

- **Scenarios** tab: multi-step wizard (basics → policy rounds → personas → groups → RAG → review), save, clone from template, export link.
- **Run** tab: scenario `<select>` populated from `GET /scenarios` (fallback to builtins if fetch fails).
