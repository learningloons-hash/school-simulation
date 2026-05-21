# senna-iter-11 closeout — Watch Live: plain-English labels

**Date:** 2026-04-20  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC3.md` § senna-iter-11.

## Shipped

- **`frontend/src/components/LiveRunDashboard.tsx`:** Removed developer note block (API path / design doc). Convergence banner uses plain copy only (no threshold/patience). Stats cards use **Discussion status** with `getRunStatusLabel` from `runStatusCopy.ts`, **Rounds completed** / **Exchanges so far**, **Participants**, **Turn style**, and **Participant pool** lines; run ID removed from this view. Section headings: **Opinion trends by round**, **Round-by-round outcomes**, **Participants**. Sparkline row titles and `Sparkline` `label` props use plain English (no raw metric keys). Agent rows show Support/Resistance/Workload as percentages and **Stance**. Outcomes table headers: Adoption score, Disagreements, Consistency score. Empty states use local `emptyStateCardStyle` (same values as `App.tsx`).  
- **`frontend/src/App.tsx`:** `LiveRunDashboard` no longer receives `runId` or `pollIntervalMs` (only used for the removed note).

## Verification

- `npm run build` in `frontend/` — PASS

## Not in scope

- senna-iter-12 (Conversation view) and later Arc 3 iterations.
