# senna-iter-13 closeout — Results tab: plain-English summary

**Date:** 2026-04-20  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC3.md` § senna-iter-13 and § *Architect / reviewer emphasis* (2).

## Shipped

- **`frontend/src/App.tsx` — Results (`outcomes`) tab**
  - **`readinessLevel()`** helper (low / moderate / high from 0–1 floats; `null` → `"unknown"`).
  - **`discussionSummaryStats`** via `useMemo`: first/last readiness and alignment from `stateTimeline`, `totalConflicts` from `outcomeIndicators`, `totalRoundsCompleted` = `stateTimeline.length`.
  - **Discussion summary** card (when `stateTimeline.length > 0`): title, rounds + optional **consensus / early stop** copy (`convergedAtRound`), readiness **from → to** with real `<strong>` elements (no tags inside template literals), agreement **rose / fell / held steady** with `%` in `<strong>`, disagreement sentence when `totalConflicts > 0`.
  - **Table** when `outcomeIndicators.length > 0`: columns Round, Adoption score, Disagreements, Consistency score; styled per handoff (`#E5E3DC`, `#F0EEE8`, `#6B7280` headers).
  - **Empty state** when both timeline and outcomes are empty (same copy as before).
  - Section heading **`Results`** (aligned with tab label). Raw `adoption=… · conflicts=…` lines removed.

## Verification

- `npm run build` in `frontend/` — PASS

## JSX note

Narrative emphasis uses JSX children (`<strong>`, fragments, ternaries) only — no `<strong>` inside interpolated strings.

## Not in scope

- senna-iter-14 (Attitudes tab) and later.
