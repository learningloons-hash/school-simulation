# Iteration 12 closeout — performance / thesis hardening

**Date:** 2026-04-04  
**Status:** Shipped (MVP scope per `BRIEF_FOR_JOAN.md` §5.1)

## Shipped

### 1. `effective_provider` + `effective_model` per turn

- SQLite: `agent_turns.effective_provider`, `agent_turns.effective_model` (nullable for legacy rows; new turns always set).
- Orchestrator: after `resolve_effective_provider`, `effective_model_id()` picks `lmstudio_model` vs `anthropic_model`.
- API: poll transcript includes both fields.
- Export: `get_simulation_export_bundle` transcript rows and ZIP `agent_turns.csv` include the new columns.
- **`export.json` `export_version`:** **`3`** (additive; consumers should tolerate unknown keys).

### 2. `POST /simulations/run` — `warnings[]`

- Non-breaking: response shape `{ "id": "<uuid>", "warnings": [] }`.
- Populated when roster CSV and/or population CSV reference **`group_ids` not defined** on the scenario’s `groups` list (human-readable strings; `config_snapshot` still has `roster_unknown_group_ids` / `population_unknown_group_ids`).

### 3. `interaction_last_k` (sample-K mode)

- For `simulation_mode === sample_k_per_round`, first turn of rounds 2+ uses a peer-history window scaled by **`len(round_agents)`** (capped at 120) instead of always using full-roster × prior rounds, reducing over-fetch when K ≪ `agent_limit`.
- **Documented formula:** ADR-001 § Per-turn LLM traceability (Iteration 12).

### 4. Stress / timing harness (tests)

- `tests/test_iteration12.py::test_stress_many_fake_llm_turns_completes_quickly` — 8 agents × 5 rounds, fake LLM, asserts completion under **5s** wall-clock (regression guard; typical run ≪ 1s).
- **`POST /simulations/run` warnings:** tests for unknown **`group_ids`** in roster CSV and in population CSV.
- Hybrid persistence test asserts alternating `effective_provider` on turns.

### 5. Frontend

- Run tab: shows server **`warnings`** after start when non-empty.
- Transcript tab: shows **LLM: provider / model** per turn when present.
- Validity copy updated to **`export_version` 3**.

## Explicitly deferred / waived

- **Parallel LLM calls / batching queue:** not implemented; sequential calls unchanged (brief “sketch” left for a later slice if architect approves).
- **`interaction_last_k` further tuning** for full round-robin: only sample-K path adjusted; full RR formula unchanged.

## Verification

- `PYTHONPATH=src pytest tests/` — **55** passed (Python 3.11).
- `npm run build` in `frontend/`.

## References

- `backend/src/mirofish_backend/llm/router.py` — `effective_model_id`
- `backend/src/mirofish_backend/db/schema.py`, `db/repo.py`
- `backend/src/mirofish_backend/simulation/orchestrator.py`
- `backend/src/mirofish_backend/api/simulations.py`
- `docs/adr/ADR-001-iteration-10-11-contracts.md` (Iteration 12 subsection)
