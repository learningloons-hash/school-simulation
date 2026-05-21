# senna-iter-8 closeout — RunStatusCard

**Date:** 2026-04-20  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC2.md` § senna-iter-8.

## Shipped

- `frontend/src/components/RunStatusCard.tsx` — empty state (`runId` null + `idle`), status copy via `getRunStatusLabel`, progress bar (blue / green when completed), **Watch Live** / **View Conversation** / **Download report ▾** (ZIP), failure banner; no run ID in card; JSON export not surfaced here (handler passed for Arc 3).

## Verification

- `npm run build` — PASS

## Post–Arc 2 review (notes)

- Progress bar blue → green on **completed** matches intent.
- `onDownloadJson` reserved with comment for Arc 3 export flow — called out as good forward hygiene.
