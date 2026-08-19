# Senna iter-48 closeout — Arc 10 baseline (arc closeout)

**Spec:** [`docs/handoffs/handoff-to-builder.md`](../handoffs/handoff-to-builder.md) **`senna-iter-48`**
**Base:** `c890c2a` (iter-47)
**Date:** 2026-08-19
**Status:** **CLOSED** — **Arc 10 CLOSED**

## Part A — iter-47 hardening

- **Rubric MD wired:** `build_judge_prompts()` loads per-category criteria from `docs/diagnostics/ARCHITECTURAL_INTERVIEW_RUBRIC.md` via `load_rubric_category_excerpt()`; inline `RUBRIC_EXCERPTS` retained as fallback only.
- **Multi-agent test:** `test_two_agents_ten_responses_and_scores` — 2 agents × 5 categories = 10 responses/scores.
- **Re-run guard:** existing interview rows detected before `--execute`; JSON error returned (no UNIQUE crash). `--force` deletes and replaces (documented here).
- **iter-45 flake / gate fix:** `test_run_persists_memory_context_export` uses `monkeypatch` on `orchestrator.llm_complete` and explicit `fidelity_tiers=[1, 1]` via shared `tests/simulation_helpers.py` — tier-3 turns skip inclusion logging, which produced empty `memory_context_log` under some setups.

## Gate fix (post–Architect review)

- **Root cause:** Tier-3 heuristic turns return before `build_memory_context_inclusion_records`; without explicit tier-1 fidelity, the integration test could assert on an empty log.
- **Fix:** Shared `memory_context_run_kwargs()` forces tier-1 agents; iter-45 and iter-48 baseline tests both use it.
- **Verification (gate fix):** `332 passed, 2 skipped` — full suite green (2026-08-19).

## Part B — Arc 10 baseline

- **`scripts/run_arc10_diagnostics.py`:** Combined JSON for memory context summary + MemBench fixtures (seed 42 default) + architectural interview (existing rows or `--execute-interview`).
- **`backend/src/mirofish_backend/diagnostics/arc10_baseline.py`:** Summary builder, hypothesis evaluation, markdown generator.
- **`docs/diagnostics/ARC10_BASELINE.md`:** Generated artifact (canonical fixture run; body reproducible except `generated_at`).
- **Hypothesis verdict:** **mixed** — recall-style avg 0.5 vs synthesis-style avg 0.375 (delta 0.125); MemBench reflective > factual on vendored fixtures; interview memory_retrieval strong, reflection weak.

## Script usage

```bash
# Combined JSON (interview rows must exist unless --execute-interview)
python3 scripts/run_arc10_diagnostics.py <simulation_id> --write-baseline

# Live interview + combined run
python3 scripts/run_arc10_diagnostics.py <simulation_id> --execute-interview --write-baseline

# Re-run interview on same sim
python3 scripts/run_architectural_interview.py <simulation_id> --execute --force
```

## Verification

```bash
cd backend && uv run pytest tests/test_senna_iter47_architectural_interview.py tests/test_senna_iter48_arc10_baseline.py -q
# → 14 passed

cd backend && uv run pytest -q
# → 332 passed, 2 skipped (2026-08-19)
```

## Notes

- `EXPORT_VERSION` stays **11** (unchanged).
- iter-45 orchestrator instrumentation and MemBench fixtures untouched.
- **Not a validity instrument** — baseline uses Arc 10 diagnostics only; no Phase V / CIEPSS numbers.

**Next:** Arc 11 memory architecture (not started).
