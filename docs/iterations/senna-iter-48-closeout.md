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

## Pass 2 remediation (2026-08-20)

Independent re-review blockers B2, B3, B5, B6 — B1/B4 left untouched.

- **B3:** MemBench factual fixtures step-aligned (`target_step_id` in range); validation applies to all cells.
- **B6:** `canonical_baseline_inputs.json` v2 = inputs only; `--from-canonical` recomputes via MemBench + interview rows.
- **B5:** `validate_interview_completeness` requires full agent×category grid from snapshot/bundle agent ids.
- **B2:** Same-round peers excluded from peer prompt; extended scan for `recency_cut`; inclusion logging after LLM.
- **Verification:** 340 passed, 2 skipped.

## Hypothesis verdict reconciliation (2026-08-20, Arc 11 blocking item 2)

This closeout originally reported **mixed** (recall 0.5 vs synthesis 0.375, delta 0.125) from the
canonical fixture *before* the B3 MemBench step-alignment fix. The committed
`docs/diagnostics/ARC10_BASELINE.md` was later regenerated *after* B3 landed and now shows
**supported** (recall 1.0 vs synthesis 0.625, delta 0.375) — same 2-item synthetic fixture, but
B3 corrected a factual-accuracy bug that had been silently dragging the pre-fix recall figure down.
Neither number was ever a real measurement; both are artifacts of the same degenerate 2-agent,
1-item-per-cell canonical bundle. Recording this rather than letting the closeout's stale figure
stand uncorrected, per GM's Arc 11 ruling.

A real baseline now exists: 3 agents, 5 rounds, live Anthropic calls, `network_bounded` visibility
with a genuine (non-fully-connected) influence network — see
`docs/diagnostics/ARC10_MEASURED_BASELINE_REAL_RUN.md` (simulation `21a6d94e0af141de95da73fc3c41f759`).
**Verdict: mixed**, delta **0.0** (recall-style avg 1.0, synthesis-style avg 1.0) — no separation at
all in this run. This is n=1 and shouldn't be over-read, but it supersedes both fixture-derived
numbers above for any claim about real Senna behavior. It also does not, on its own, support
reflection as Arc 11's highest-priority mechanism — consistent with treating iter-51's real
Phase V-hypothesis test (not this fixture-based one) as the actual decision point per
`HANDOFF_SENNA_ARC11.md`.

Also from the real run: **group-addressed proportion 0.666667** (10/15 turns), not the fixture's
1.0. `visibility_policy` accounted for 10 of 89 inclusion-log exclusions — the network genuinely
filtered some direct/targeted turns, so the influence-network mechanism is not inert in this run.
Flagged to Mark directly per his standing instruction, not folded quietly into this note.
