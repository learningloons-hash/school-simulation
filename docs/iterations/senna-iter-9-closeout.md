# senna-iter-9 closeout — Run history redesign

**Date:** 2026-04-20  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC2.md` § senna-iter-9.

## Shipped

- **Recent discussions** cards: scenario display name from catalog, `formatRunDate`, status pill via `classifyRunStatusTone` + `RUN_STATUS_PILL_STYLES` + `shortStatusLabel`, rounds summary, **Open** / **Download**; no monospace id on card face.
- **Open** calls `loadRunById(id, { switchTab: true })` — navigates to Watch Live when `running`/`starting`, Conversation when `completed`.
- Auto-refresh when `activeTab === "controls"`; **↻ Refresh** control next to section title.
- **Load a previous discussion by ID** block with styled input + secondary **Load** button.
- `RUN_STATUS_PILL_STYLES` + `shortStatusLabel` live in [`frontend/src/lib/runStatusCopy.ts`](../../frontend/src/lib/runStatusCopy.ts); `SennaHeader` imports shared pill map.

## Notes

- `SimulationListItem` has no `agent_limit` — participant count line omitted per handoff.

## Verification

- `npm run build` — PASS

## Post–Arc 2 review (notes)

- **Open** + `loadRunById(..., { switchTab: true })` auto-navigation (Watch Live vs Conversation) noted as a solid UX enhancement.
