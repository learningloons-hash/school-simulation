# Senna iter-44 closeout — Arc 9 integration, LICENSE, proposal wording

**Spec:** [`docs/handoffs/HANDOFF_SSTRF_ARC9_STUDY_INSTRUMENTS.md`](../handoffs/HANDOFF_SSTRF_ARC9_STUDY_INSTRUMENTS.md) **`## senna-iter-44`**.
**Date:** 2026-08-18
**Status:** **CLOSED**

## Product repo (`main`)

| Deliverable | SHA / artifact | Result |
|-------------|----------------|--------|
| Commit split (iter-40) | `9d5c637` | Pushed `origin/main` |
| `main`-only test isolation | `uv run pytest` | **302 passed, 2 skipped** |
| Apache 2.0 `LICENSE` | repo root | Copyright 2026 Ministry of Education, Singapore (Mark-confirmed) |
| Cost re-measurement (Likert on vs off) | `test_sstrf_arc9_integration.py::test_arc9_cost_remeasurement_likert_adds_billing_rows` | Likert adds 3 billing rows / `likert_self_report_turns` on stub path |
| Non-study simulation + Likert E2E | `test_arc9_non_study_simulation_with_likert_persists_rows` | `fsbb_comparator`, ≥9 Likert rows persisted |

## Study repo (`sstrf-local` → `study/main`)

| Deliverable | SHA / artifact | Result |
|-------------|----------------|--------|
| iter-41/42 remediation commit | `1a442df` | Pushed `study/main` |
| iter-43 (prior) | `29c25bf` | Already on study branch |
| Non-CIEPSS elicitation dry run | `test_arc9_elicitation_dry_run_non_ciepss_study_id` | `study_id=fsbb_dry_run_v1`, `execute=False`, 3 agents |
| Plausibility packet pipeline | `test_arc9_plausibility_packets_from_non_study_bundle` | Leakage-clean blind packets + key round-trip |
| Proposal wording | `simulation-study/Proposal.docx` | Replaced “adapted from the open-source MiroFish architecture” → “designed with reference to the open-source MiroFish architecture; independently implemented” |
| Full Arc 9 suite (mixed tree) | `uv run pytest` | See verification line below |

## Verification

```bash
# Product isolation (iter-40 gate)
git checkout main && cd backend && uv run pytest -q
# → 302 passed, 2 skipped

# Arc 9 integration + study tests (sstrf-local)
git checkout sstrf-local && cd backend && uv run pytest -q
# → 407 passed, 2 skipped (2026-08-18)
```

## Arc 9 Definition of Complete — checklist

1. **All five gates iter-40…44** — PASS (this closeout + prior iter closeouts).
2. **Likert supplements float; convergence unchanged when disabled** — PASS (`test_senna_iter40_likert`, diff review).
3. **Elicitation parameterized; CIEPSS regression + non-CIEPSS dry run** — PASS (iter-41 tests + arc9 integration test).
4. **Plausibility packets pass zero-tolerance leakage check** — PASS (iter-42 tests + arc9 integration test).
5. **Calibration harness 1-vs-2 + double-miss gate** — PASS (iter-43, `test_sstrf_rq1_scoring.py`).
6. **LICENSE on product repo** — PASS (`LICENSE`, Apache 2.0, MOE copyright).
7. **Proposal wording on study repo** — PASS (`simulation-study/Proposal.docx`).
8. **Artifacts on correct repo/branch** — PASS (§0 split: `9d5c637` main, `1a442df` study).

**Arc 9: CLOSED.**
