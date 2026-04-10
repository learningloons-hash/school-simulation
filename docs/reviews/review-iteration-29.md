# Review: Iteration 29
Date: 2026-04-08
Reviewer: Claude Opus (Architect)
Verdict: PASS

## Iteration Delta

- New `simulation/economics.py` module: `PROVIDER_PRICE_MAP` (snapshot pricing), `estimate_cost_usd`, `_turn_cost_usd`, `tier_breakdown_from_transcript`, `build_run_economics_payload` — all pure functions, env-overridable.
- `LLMCompletion` dataclass on `llm/router.py`: `input_tokens` / `output_tokens` propagated from Anthropic + LM Studio clients.
- Orchestrator accumulates tokens per round via `_TurnOutcome`, persists with `update_simulation_token_totals`.
- DB: `simulation_runs.total_input_tokens`, `total_output_tokens`; `agent_turns.input_tokens`, `output_tokens` (nullable). Schema migration via `_ensure_column`.
- `GET /simulations/{id}`: `economics` object with token totals, `estimated_cost_usd`, `llm_provider`, `tier_breakdown`.
- `GET /experiments/{id}`: per-run `economics`, `total_estimated_cost_usd` aggregate.
- Export version **8**: `run.economics` in JSON; token columns in `agent_turns.csv`; `input_tokens`, `output_tokens`, `estimated_cost_usd` in experiment `comparison.csv`.
- `GET /capabilities`: `economics` description with `PRICE_MAP_DATE`.
- Frontend: Run metadata panel shows economics; Experiments tab shows per-run tokens/cost and experiment total; comparison table header hints include cost.

## Critical Issues

None.

## Important Issues

None.

## Minor Issues

### M1: `estimate_cost_usd` ignores `provider_key` parameter after the early return
- Severity: MINOR
- Files: `backend/src/mirofish_backend/simulation/economics.py` (lines 31–42)
- Problem: The function accepts `provider_key` but after the `lmstudio` early-return, it always calls `_per_mtok_rates("anthropic")` regardless of the actual `provider_key` value. If a new provider (e.g. `openai`, `google`) is added in the future, this function would apply Anthropic pricing to it. Currently harmless because only `anthropic`, `lmstudio`, and `hybrid` exist, and `hybrid` deliberately uses Anthropic rates.
- Fix: Pass `provider_key` instead of hardcoded `"anthropic"` to `_per_mtok_rates`. This is a 1-line change that makes the function future-proof. Not urgent.

### M2: `_turn_cost_usd` only bills `"anthropic"` — `hybrid` turns attributed to LM Studio get $0
- Severity: MINOR (correct for now, needs documentation)
- Files: `backend/src/mirofish_backend/simulation/economics.py` (lines 45–53)
- Problem: `_turn_cost_usd` checks `effective_provider == "anthropic"` at the per-turn level, which is the correct granularity for hybrid runs — only actual Anthropic calls are costed. However, the `PROVIDER_PRICE_MAP` has `"hybrid": $3/$15`, which implies hybrid runs should be fully costed at Anthropic rates. This is intentional (documented as "upper-bound envelope" in `estimate_cost_usd`) but creates two different answers for the same run: `estimate_cost_usd` with `provider_key="hybrid"` gives the worst-case; `estimated_run_cost_usd_from_transcript` gives actual per-turn cost. The code uses the per-turn version, which is more accurate, but the `hybrid` entry in `PROVIDER_PRICE_MAP` is now dead code.
- Fix: Remove `"hybrid"` from `PROVIDER_PRICE_MAP` or add a comment explaining it exists only for external callers (e.g. pre-run cost estimation). Minor — not a bug.

### M3: No unit test for `economics.py` pure functions in isolation
- Severity: MINOR
- Files: `backend/tests/test_iteration29.py`
- Problem: The three E2E tests exercise economics through the full HTTP stack, which is good for integration coverage. However, the pure functions (`estimate_cost_usd`, `_turn_cost_usd`, `tier_breakdown_from_transcript`, `build_run_economics_payload`) are not tested directly. Edge cases like `input_tokens=None`, `provider_key="unknown_future_provider"`, or an empty transcript are only covered implicitly.
- Fix: Add a small unit test file or section testing `estimate_cost_usd` for each provider key, the `None` handling in `_turn_cost_usd`, and `tier_breakdown_from_transcript` with mixed tiers. Low priority — current E2E tests are sufficient for the thesis.

### M4: Token totals duplicate information
- Severity: MINOR (design trade-off, not a bug)
- Files: `backend/src/mirofish_backend/db/repo.py`
- Problem: `total_input_tokens` / `total_output_tokens` on `simulation_runs` are denormalised — they're the sum of `agent_turns.input_tokens` / `output_tokens` for that simulation. The orchestrator updates them after each round for performance (avoids re-summing all turns on every poll). If a turn row is ever deleted or modified, the totals become stale. Currently there's no mutation path for turn rows, so this is safe.
- Fix: None needed now. If turn mutation is ever added, add a trigger or recomputation step. Document the invariant.

### M5: Test `estimated_cost_usd == 0.0` for lmstudio runs — assertion could mask bugs
- Severity: MINOR
- Files: `backend/tests/test_iteration29.py` (line 128)
- Problem: `test_experiment_detail_has_total_estimated_cost_and_comparison_csv_columns` asserts `total_estimated_cost_usd == 0.0` because the fake LLM defaults to the `lmstudio` provider. A test using a fake Anthropic provider (with `monkeypatch` for the API key check) that returns non-zero costs would exercise the full pricing path.
- Fix: Add a test variant that sets `llm_provider="anthropic"` and verifies `estimated_cost_usd > 0`. Low priority.

## Architecture Alignment

| Component | Status | Gap |
|-----------|--------|-----|
| Orchestrator | ✅ | `_TurnOutcome` extended cleanly; token accumulation after `asyncio.gather` is correct |
| LLM Router | ✅ | `LLMCompletion` dataclass is backwards-compatible; both clients extract usage |
| LLM Clients | ✅ | Anthropic: `usage.input_tokens`/`output_tokens`. LM Studio: `prompt_tokens` with `input_tokens` fallback; `completion_tokens` with `output_tokens` fallback |
| Economics Module | ✅ | Clean pure-function design; env-overridable pricing; snapshot date for thesis citation |
| Data Model | ✅ | Additive columns via `_ensure_column`; no breaking changes |
| API | ✅ | `economics` object well-structured; experiment detail includes per-run + aggregate |
| Export | ✅ | Version 8; token columns in `agent_turns.csv`; cost columns in `comparison.csv` |
| Frontend | ✅ | Run metadata economics panel; Experiments per-run + total; comparison header hints |
| Config/Reproducibility | ✅ | `PRICE_MAP_DATE` persisted in capabilities; `llm_provider` in economics payload |
| Experiments | ✅ | Per-run economics + `total_estimated_cost_usd` aggregate |

## What's Good

- **Clean module boundary.** `simulation/economics.py` is a standalone pure-function module with no DB imports or side effects. Easy to unit test, easy to swap pricing strategies.
- **`LLMCompletion` dataclass is the right abstraction.** Instead of returning a tuple or dict, the router returns a typed object. Both clients extract `usage` defensively (try/except, None fallback).
- **Token accumulation is round-level, not turn-level.** The orchestrator accumulates `run_in_acc` / `run_out_acc` across all turns in the round's `asyncio.gather`, then writes a single DB update per round. This avoids N DB writes per round (one per turn) and is consistent with the existing round-level pattern for status updates.
- **`_turn_cost_usd` uses `effective_provider`, not `llm_provider`.** For hybrid runs, this means only actual Anthropic API calls are costed — LM Studio turns in a hybrid run correctly show $0. This is more accurate than applying a blanket rate to all turns.
- **Experiment-level aggregate is derived, not stored.** `total_estimated_cost_usd` is computed on read by summing per-run costs. No denormalisation risk.
- **Env-overridable pricing with snapshot date.** When Anthropic changes pricing (they will), the researcher updates two env vars and the PRICE_MAP_DATE. No code change needed.
- **`comparison.csv` includes token/cost columns per run.** This is the direct data source for the thesis RQ2 cost comparison — ready to paste into a LaTeX table.

## Next Steps for Builder

### Priority 1 (recommended improvements)
1. Add a test with `llm_provider="anthropic"` that verifies non-zero `estimated_cost_usd` (M5).
2. Pass `provider_key` through in `estimate_cost_usd` instead of hardcoded `"anthropic"` (M1).

### Priority 2 (backlog)
3. Unit tests for `economics.py` pure functions (M3).
4. Clarify `hybrid` in `PROVIDER_PRICE_MAP` with a comment (M2).
5. Real-time cost ticker during live runs (from iteration 29 closeout backlog).
6. Hard pre-run cost cap.

## Test Requirements

For the PASS verdict to hold:
1. Existing `test_iteration29.py` (3 tests) continue passing.
2. Frontend `npm run build` passes.

---

## Follow-up resolution (2026-04-08)

Builder applied recommended **Priority 1** items and **M2–M4** documentation/tests:

| Item | Resolution |
|------|------------|
| **M1** | `estimate_cost_usd` now calls `_per_mtok_rates(pk)` so non-`lmstudio` keys use `PROVIDER_PRICE_MAP` (unknown keys still fall back to anthropic rates in `_per_mtok_rates`). |
| **M2** | Comment on `PROVIDER_PRICE_MAP["hybrid"]` documents envelope-only use vs per-turn billing. |
| **M3** | `test_economics_pure_functions` covers `estimate_cost_usd`, `estimated_run_cost_usd_from_transcript`, `tier_breakdown_from_transcript`, `build_run_economics_payload`. |
| **M4** | Denormalised run totals invariant documented in `iteration-29-closeout.md` § Design notes. |
| **M5** | `test_get_simulation_anthropic_provider_positive_estimated_cost` — `llm_provider=anthropic` + fake LLM → `estimated_cost_usd` ≈ 0.0012 for 2 turns. |

Suite: **191 passed, 1 skipped** (`tests/test_iteration29.py` now 5 tests).
