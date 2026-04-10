# Iteration 6 closeout

**Project:** `mirofish-mvp`  
**Gate date:** 2026-04-02  
**Status:** Implementation complete.

## Scope (from SESSION_STATE)

| Item | Shipped |
|------|---------|
| Validity notes data model | `validity_notes` SQLite table + repo helpers |
| Face / construct / predictive | Optional `*_score` REAL + `*_rubric` TEXT each |
| Per run or per round | `round_number` NULL = run-level |
| Timestamps / rater | `created_at`, optional `rater_id` |
| API + export | POST create, GET status + export bundle + ZIP CSV |
| Minimal UI | **Validity** tab with form + list |
| Optional state audit flag | `state_audit_enabled` in Settings + `config_snapshot`; **no auditor LLM** when false |

## Schema (`validity_notes`)

| Column | Type |
|--------|------|
| id | TEXT PK |
| simulation_id | TEXT FK → simulation_runs |
| round_number | INTEGER NULL |
| rater_id | TEXT NULL |
| face_score, construct_score, predictive_score | REAL NULL |
| face_rubric, construct_rubric, predictive_rubric | TEXT NULL |
| notes | TEXT NULL |
| created_at | TIMESTAMP |

## API

- **`POST /simulations/{simulation_id}/validity-notes`** — JSON body `ValidityNoteCreate`; returns `{"id": "<hex>"}`.
- **`GET /simulations/{id}`** — adds **`validity_notes`** (chronological).
- **`GET /simulations/{id}/export.json`** — **`export_version`: `"2"`**, bundle key **`validity_notes`**.
- **`GET /simulations/{id}/export.zip`** — **`validity_notes.csv`**.

## Config

- **`STATE_AUDIT_ENABLED`** (bool, default false) → **`state_audit_enabled`** in **`config_snapshot`** for runs started after deploy. Reserved for a future second-pass state parse / auditor prompt.

## Key files

| Area | Path |
|------|------|
| Migration / table | `backend/src/mirofish_backend/db/schema.py` |
| Repo | `backend/src/mirofish_backend/db/repo.py` (`insert_validity_note`, `_get_validity_notes`, `simulation_exists`, `get_simulation_total_rounds`) |
| API | `backend/src/mirofish_backend/api/simulations.py` |
| Config | `backend/src/mirofish_backend/config.py` |
| ZIP | `backend/src/mirofish_backend/export_bundle.py` |
| Tests | `backend/tests/test_validity_notes.py`, `test_export_bundle.py` |
| UI | `frontend/src/App.tsx`, `frontend/src/lib/api.ts` |

## Gate evidence

```bash
cd backend && PYTHONPATH=src pytest tests/ -q   # 24 passed
cd ../frontend && npm run build
```

## Deferred

- Implementing an actual **auditor** LLM pass when `state_audit_enabled` is true (Iteration 7+ or separate slice).
- PATCH/DELETE for validity notes (append-only for now).
