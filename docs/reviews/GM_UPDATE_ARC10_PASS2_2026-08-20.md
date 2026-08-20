# Arc 10 Pass-2 Re-Review — Update for GM

Prepared by Ops for Mark, to table with GM.

## Bottom line

Arc 10 pass-2 (`main`@`906fb38`) re-reviewed independently against `docs/reviews/independent-review.md`'s six blockers. **Verdict: PASS_WITH_ISSUES**, overall — up from the original review's FAIL. Five of six blockers are clean, verified passes; one (B2) has a real fix for its correctness bugs but a residual coverage gap. Suite: `340 passed, 2 skipped`, confirmed by direct execution, exact match to expected.

## Per-blocker verdict

| Blocker | Verdict | Note |
|---|---|---|
| B1 (should remain PASS) | **PASS** | Race fix holds — re-ran the flaky test 5x, no failures. |
| B2 | **PASS_WITH_ISSUES** | Prompt-alignment and visibility-label bugs genuinely fixed and verified. Residual: no scale/row-volume test was added (explicitly requested in the original fix instruction), and a bounded extra DB read before LLM execution remains (now capped at 24 rows, down from whatever produced the original "10,000-row" complaint — real severity reduction, not eliminated). |
| B3 | **PASS** | Verified programmatically — every MemBench fixture's QA target now falls inside the retained trajectory. |
| B4 (should remain PASS) | **PASS** | Unparseable judge output is excluded from averages, not silently zeroed. |
| B5 | **PASS**, exceeds the ask | Exact agent×category grid validation, plus outright rejection of any unparseable judge row — stronger than the literal fix instruction. |
| B6 | **PASS**, one minor caveat | Canonical baseline now regenerates from committed inputs with full provenance; regression test proves byte-identical reproduction. Caveat: the recorded `code_revision` field reads the pass-1 commit, not pass-2, for a file pass-2 itself regenerated — likely just stale, not re-verified since. |

## Two follow-ups, not re-blocking Arc 10

1. **B2's scale/row-volume test gap.** The correctness bugs are fixed; what's missing is a regression proving the (now-bounded) extra read stays cheap as run size grows. Low urgency given the 24-row cap, but was explicitly asked for and wasn't delivered.
2. **Broken closeout links.** `senna-iter-45/46/47` closeouts still point to `HANDOFF_SENNA_ARC10_MEMORY_DIAGNOSTICS.md`, which no longer exists on `main` (superseded by `handoff-to-architect.md`/`handoff-to-builder.md`; only `iter-48`'s closeout was updated). Matches the original review's Warning #5, still open.

## Ask

Mark's proposal: rather than opening a pass-3 remediation cycle on Arc 10 for these two items, fold both into Arc 11's handoff as required opening work — Arc 11 already touches the memory-context/orchestrator code path (importance scoring, retrieval, reflection), so the scale test and link fix are cheap to pick up there and don't block Arc 10 closing now. **If GM agrees**, Ops will bake both into the Arc 11 handoff's scope explicitly (not just log them) before Arc 11 is expanded for Architect. If GM prefers a clean pass-3 close on Arc 10 first, Ops will do that instead.

Full detail: `docs/reviews/independent-review.md` (original), Ops's verification in this conversation thread.
