# senna-iter-4 closeout — Plain-English run status

**Date:** 2026-04-20  
**Scope:** `HANDOFF_SENNA_ARC1.md` § senna-iter-4.

## Shipped

- `frontend/src/lib/runStatusCopy.ts` — shared helpers: `getRunStatusLabel`, `getProgressLine`, `classifyRunStatusTone`.
- **Current run** block: status line and progress line use mapping; footnote and “exchanges recorded” line updated; start button states (“Starting…”, “Running…”, “Start discussion”).
- **Recent runs** list in Controls: each row status uses `getRunStatusLabel` (no raw `running` / `completed` tokens).
- **Run Details** tab: status line uses same mapping.
- Open-by-ID input placeholder updated.

## Verification

- Convergence completion copy uses `convergedAtRound` when present on loaded run.
- `error:` statuses show trimmed message with `Error:` prefix.
- `npm run build` — PASS

## Notes

- `LiveRunDashboard` may still show raw API status internally; handoff scoped primary UX to Set Up & Run / shared header (iter 5).
