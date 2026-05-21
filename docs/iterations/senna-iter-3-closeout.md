# senna-iter-3 closeout — Tab labels & grouping

**Date:** 2026-04-20  
**Scope:** `HANDOFF_SENNA_ARC1.md` § senna-iter-3.

## Shipped

- All 10 tab **display** labels updated; internal `TabId` values unchanged.
- Tab bar split into **primary** (Set Up & Run, Watch Live, Conversation, Results, Attitudes) and **secondary** (Compare Runs, Assistant, Policy Scenarios, Quality Notes, Run Details) with a thin vertical divider.
- Cross-tab empty states updated from “Run tab” to “Set Up & Run” where they referred to navigation.
- Run Details panel `<h2>` aligned with tab name.

## Verification

- Tab switching unchanged (`TabId` stable).
- `npm run build` — PASS
