# senna-iter-22 closeout — Typography & numeric formatting

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC5.md` § **senna-iter-22** (Parts A–C, Definition of done).

## Shipped

### `frontend/src/App.tsx`

- Import **`FONT`** from `./lib/theme`.
- **Results** tab — outcome indicators table: **Round** column unchanged (sans-serif); **Adoption score**, **Disagreements**, and **Consistency score** cells use `fontFamily: FONT.mono`, `fontSize: 13`, `#1A1A1A`.
- **Run Details:** `<h2>` replaced with styled `<div>` (18px, 600, `#1A1A1A`, `marginBottom: 20`, `marginTop: 0`).
- **Run Details spacing:** Download block `marginBottom` **0**; **Session ID** row **`marginTop: 16`** for a consistent 16px gap after Download.
- **Quality notes:** `<h2>` replaced with styled `<div>` (18px, 600, `#1A1A1A`, `marginBottom: 16`). Score field grid already **`gap: 8`** — unchanged.

### `frontend/src/components/ExperimentConsole.tsx`

- Import **`FONT`** from `../lib/theme`.
- **All metrics by round** table: data `<td>` cells (not Round) use **`fontFamily: FONT.mono`** with existing `fontSize: 11`.
- Experiment id / list id snippets: **`FONT.mono`** instead of string **`"monospace"`**.

### `frontend/src/components/LiveRunDashboard.tsx`

- Import **`FONT`** from `../lib/theme`.
- **Round-by-round outcomes** table: **Round** sans-serif; numeric columns use **`FONT.mono`**, `fontSize: 13`, **`#1A1A1A`**.

## Verification

- `npm run build` in `frontend/` — **PASS** (`vite build`).
- `rg '<h2' frontend/src/App.tsx` — **no matches**.
- `rg 'monospace' frontend/src/components/ExperimentConsole.tsx` — **no matches**.

## Not in scope

- Tab bar (senna-iter-23); backend.
