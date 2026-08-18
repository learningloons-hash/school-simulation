# Senna iter-47 closeout — Architectural diagnostic interview

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC10_MEMORY_DIAGNOSTICS.md`](../handoffs/HANDOFF_SENNA_ARC10_MEMORY_DIAGNOSTICS.md) **`senna-iter-47`** (Arc 10)
**Base:** `1bdb199` (iter-46)
**Date:** 2026-08-18
**Status:** **CLOSED**

## Delivered

- **`backend/src/mirofish_backend/diagnostics/architectural_interview.py`:** Five-category question bank (product-safe wording); one LLM call per agent per category; post-run administration via `run_architectural_interview_for_simulation`; `complete_with_profile` uses existing `llm_complete` + Arc 7/8 `model_profile_id`.
- **`backend/src/mirofish_backend/diagnostics/judge_score_parse.py`:** Rubric judge parse with provenance (`model_parsed` / `repaired` / `keyword_fallback`); `<judge_score>{...}</judge_score>` block discipline (Likert-parse lineage).
- **`docs/diagnostics/ARCHITECTURAL_INTERVIEW_RUBRIC.md`:** Written 0–2 rubric per Park category; rubric version `1`.
- **`scripts/run_architectural_interview.py`:** CLI post-run runner (dry-run default; `--execute` for live LLM).
- **`backend/src/mirofish_backend/db/schema.py`:** `architectural_interview_responses` + `architectural_interview_scores` tables (separate from Likert / elicitation / memory context).
- **`backend/src/mirofish_backend/db/repo.py`:** insert/query; export bundle keys `architectural_interview_responses` / `architectural_interview_scores`.
- **`backend/src/mirofish_backend/export_bundle.py`:** `EXPORT_VERSION = "11"`; ZIP CSVs for interview responses/scores.
- **`GET /simulations/{id}/architectural-interview-report`:** JSON summary (mirrors memory-context-report pattern).
- **`backend/tests/test_senna_iter47_architectural_interview.py`:** Mocked LLM; calibration; malformed judge; two judge profiles; export v11; Likert separation.

## Rubric scale

**0–2 integer** per category: 0 = inadequate, 1 = partial, 2 = adequate (see rubric MD).

## Administration pattern

**One LLM call per agent per category** (5 interview + 5 judge calls per agent). Script-driven post-run only — not live orchestrator.

## Script usage

```bash
# Plan only (no LLM)
python3 scripts/run_architectural_interview.py <simulation_id>

# Run interview + judge scoring
python3 scripts/run_architectural_interview.py <simulation_id> --execute \
  --interview-profile-id local_lmstudio_default \
  --judge-profile-id anthropic_default
```

## Verification

```bash
cd backend && uv run pytest tests/test_senna_iter47_architectural_interview.py -q
# → 7 passed

cd backend && uv run pytest -q
# → 325 passed, 2 skipped (2026-08-18)
```

## Notes

- **Not a validity instrument** — measures which memory/context architectural component may be failing; no CIEPSS / Phase V comparison.
- iter-45 memory context and iter-46 MemBench adapter **untouched**.
- Judge infrastructure is iter-47 scoped only (not a general-purpose rubric framework).

**Next:** **senna-iter-48** — run all three diagnostics together + `docs/diagnostics/ARC10_BASELINE.md`.
