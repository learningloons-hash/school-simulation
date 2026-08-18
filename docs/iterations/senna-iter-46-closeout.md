# Senna iter-46 closeout — MemBench adapter

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC10_MEMORY_DIAGNOSTICS.md`](../handoffs/HANDOFF_SENNA_ARC10_MEMORY_DIAGNOSTICS.md) **`senna-iter-46`** (Arc 10)
**Base:** `e644a28` (iter-45)
**Date:** 2026-08-18
**Status:** **CLOSED**

## Delivered

- **`scripts/membench_adapter.py`:** Fixture loader; `SennaMemBenchAgent` runner (participation/observation message flow); MemBench-native **memory accuracy** scoring (exact `ground_truth` letter match per `Membenenv.py`); CLI `run`.
- **`backend/tests/fixtures/membench/`:** Four vendored trajectory JSON files + **`README.md`** (upstream URL, commit `f66d8d1028d3f68627d00f77a967b93fbb8694b6`, MIT notice, subset table).
- **`backend/tests/test_membench_adapter.py`:** Offline fixtures; separate factual/reflective reports; determinism; license README; no network in CI.

## Scoring (MemBench-native)

- **Factual vs reflective:** separate fixture files and score reports (low-level vs high-level memory content per MemBench dataset split).
- **Metric:** memory accuracy = fraction of trajectories where predicted choice letter equals `QA.ground_truth` (same rule as upstream `MemBenchEnv.step`).

## Verification

```bash
cd backend && uv run pytest tests/test_membench_adapter.py -q
# → 9 passed

cd backend && uv run pytest -q
# → 318 passed, 2 skipped (2026-08-18)
```

## Notes

- iter-45 instrumentation untouched.
- Stub agents (`memory_match`, `ground_truth`) only — live LLM MemBench runs deferred.

**Next:** **senna-iter-47** (per Arc 10 handoff).
