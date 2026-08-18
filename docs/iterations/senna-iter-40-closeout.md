# Senna iter-40 closeout — Round-end Likert self-report

**Spec:** [`docs/handoffs/HANDOFF_SSTRF_ARC9_STUDY_INSTRUMENTS.md`](../handoffs/HANDOFF_SSTRF_ARC9_STUDY_INSTRUMENTS.md) **`## senna-iter-40`**.
**Branch:** **`main`** (product repo) — per Arc 9 handoff §0. **Status at time of writing: implemented on disk, but committed nowhere.** All of iter-40 is currently sitting as uncommitted/untracked changes on the `sstrf-local` working tree, mixed with iter-41/42 remediation. This entry documents what's on disk now; it is not a shipped/closed gate until the commit split below lands on `main`.

## Shipped (on disk, uncommitted)

- **`backend/src/mirofish_backend/llm/likert_parse.py`** (new): three-tier parse/provenance for round-end Likert responses (`model_parsed`/`repaired`/`keyword_fallback`), `LIKERT_ORDINAL_FLOAT_MAP` for the six-anchor → 0–1 mapping.
- **`backend/src/mirofish_backend/simulation/likert.py`** (new): `parse_anchor_labels`, `resolve_likert_anchor_labels` (scenario + persona override), `resolve_likert_indicators`, `resolve_likert_enabled` (request flag with scenario-declared default), `float_value_for_indicator` (bridges to the existing float state for divergence reporting), and `format_likert_visible_history` — grounds the round-end prompt in the agent's actual recent visible turns (capped at 8000 chars) rather than asking for self-report in a vacuum. This grounding step is the fix for the defect the independent review flagged pre-remediation.
- Platform wiring (modified, uncommitted): `simulation/orchestrator.py` (+200 lines — round-end collection step), `db/schema.py` (+29 — new persistence columns/table), `db/repo.py` (+113 — persistence functions), `api/simulations.py` (+39 — request field), `export_bundle.py` (+24 — export path), `scenarios/registry.py` (+20 — anchor-label schema), `scenarios/validate.py` (+13 — anchor validation), `scenarios/data/fsbb_comparator.yaml` (+24 — non-study scenario example anchors), `simulation/economics.py` (+36) and `simulation/preflight.py` (+4) — cost accounting for the added round-end call.
- **`backend/tests/test_likert_parse.py`**, **`backend/tests/test_senna_iter40_likert.py`** (new).
- `backend/tests/test_iteration28.py`, `test_iteration29.py` — updated for the economics/cost changes above.

## Acceptance (per handoff spec — verify against handoff before marking PASS)

- Flag-off path byte-for-byte unchanged from pre-Arc-9 — **not independently re-verified by Ops**; Architect to confirm on `main` after the split, since this repo's suite currently runs mixed with study-repo files and isn't a clean `main`-only signal.
- `_population_convergence_delta()` untouched — confirmed by Ops via diff inspection of `orchestrator.py`: convergence logic is not among the changed hunks description in the diff stat, but Architect should confirm by direct diff review before closing, per the handoff's explicit instruction that this needs a diff review, not just a passing test.
- Divergence between float and Likert computable directly from export — not independently verified by Ops.

## Verification

- Full suite (mixed working tree, `sstrf-local`, all of iter-40 + iter-41/42 remediation + iter-43 together): **403 passed, 2 skipped** (Ops-verified, 2026-08-18).
- **Not yet verified on a clean `main`-only checkout** — this is the actual gate; the mixed-tree number above confirms the code doesn't crash, not that iter-40 is correctly isolated to product-repo scope.

## Outstanding before this gate can close

1. Commit split onto `main` (see `docs/handoffs/HANDOFF_SSTRF_ARC9_STUDY_INSTRUMENTS.md` §0 and the Ops note in `senna-iter-41-closeout.md`/`senna-iter-42-closeout.md` remediation sections for the exact file list and commands).
2. Re-run the full suite from a clean `main` checkout with only iter-40's files applied, confirm it's still 403/2 (or whatever the product-repo-only subset should read).
3. Architect diff-reviews `_population_convergence_delta()` specifically, per the D2 non-negotiable.

## Next

- **senna-iter-44** — Arc 9 integration, LICENSE, proposal wording. Blocked on the commit split above landing first.
