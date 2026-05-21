# senna-iter-5 closeout — SennaHeader

**Date:** 2026-04-20  
**Scope:** `HANDOFF_SENNA_ARC1.md` § senna-iter-5.

## Shipped

- `frontend/src/components/SennaHeader.tsx` — logo mark (10px CSS circle `#4A6FA5`), wordmark, tagline, right-aligned status pill with tone colours from spec; bottom border and `#F7F6F2` header background.
- `App.tsx` — renders `<SennaHeader status={…} />` at top; page shell uses warm background and system font stack to match header.

## Verification

- Pill uses `getRunStatusLabel` + `classifyRunStatusTone` (same mapping as iter 4).
- `npm run build` — PASS

## Notes

- Long status sentences wrap inside pill (`maxWidth`); acceptable for MVP until Arc 5 typography pass.

## Post-review fixes

**Date:** 2026-04-20

1. **Scenario dropdown** — Option labels show scenario **name only** (removed `(builtin)` / `, RAG` suffixes from `App.tsx` policy scenario `<select>`).
2. **Sampling report placement** — Removed sampling report link from the **Current run** export button row; added **Sampling report** (no “JSON” in the label) at the **bottom of Run Details**, after config snapshot content, same visibility rule (`runId` and `status === "completed" || status === "failed"`).
3. **Failure copy** — Current run and Run Details failure banners use **Something went wrong:** instead of **Failure** / `Failure:`.

**Build:** `npm run build` in `frontend/` — **PASS** (post-review).
