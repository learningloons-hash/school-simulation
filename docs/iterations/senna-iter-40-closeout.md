# Senna iter-40 closeout — Round-end Likert self-report

**Spec:** [`docs/handoffs/HANDOFF_SSTRF_ARC9_STUDY_INSTRUMENTS.md`](../handoffs/HANDOFF_SSTRF_ARC9_STUDY_INSTRUMENTS.md) **`## senna-iter-40`**.
**Branch:** **`main`** (product repo).
**Status:** **CLOSED** — `9d5c637` on `origin/main` (2026-08-18).

## Shipped

- **`backend/src/mirofish_backend/llm/likert_parse.py`** — three-tier parse/provenance for round-end Likert responses.
- **`backend/src/mirofish_backend/simulation/likert.py`** — anchor resolution, visible-history grounding, round-end collection helpers.
- Platform wiring: orchestrator, schema/repo, API flag, export bundle, scenario anchor schema + `fsbb_comparator` example anchors, economics cost accounting.
- Tests: `test_likert_parse.py`, `test_senna_iter40_likert.py`; iteration 28/29 economics tests updated.

## Acceptance

- Flag-off path unchanged (legacy tests green on `main`-only checkout).
- `_population_convergence_delta()` inputs unchanged — verified by diff review (D2).
- Divergence computable from export when flag on.

## Verification

- **`main`-only checkout:** `302 passed, 2 skipped` (2026-08-18) — iter-40 isolated from study-repo tests.
- Mixed `sstrf-local` tree (Arc 9 full): see iter-44 closeout for combined suite count.

## Next

- **senna-iter-44** — integration, LICENSE, proposal wording (product + study split).
