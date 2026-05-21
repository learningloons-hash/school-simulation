# senna-iter-10 closeout — Set Up & Run layout & empty states

**Date:** 2026-04-20  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC2.md` § senna-iter-10.

## Shipped

- Two-column grid for Set Up &amp; Run (`viewportWidth` / `resize`, breakpoint **700px**); left = setup card, right = `RunStatusCard` + history + load-by-ID.
- Shared `cardStyle` / `emptyStateCardStyle` constants in `App.tsx`.
- Empty states (white card, centred `#6B7280` copy): **Conversation**, **Results**, **Attitudes**, **Run Details** (config snapshot area).

## Verification

- `npm run build` — PASS

## Post-review fixes (Arc 2 gate)

**Date:** 2026-04-20

1. **Tab active styling** — `tabStyle` in `App.tsx`: active tab uses `#EEF3FA` background and `#4A6FA5` border (aligned with selected scenario card); inactive tabs use `#FFFFFF` / `#E5E3DC` border instead of lavender `#eef` / `#ccc`.
2. **Watch Live empty state** — When no `runId`, empty copy is wrapped in `emptyStateCardStyle` like the other polished tabs.

**Build:** `npm run build` in `frontend/` — **PASS** (post-review).
